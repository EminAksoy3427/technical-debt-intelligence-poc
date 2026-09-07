import inspect
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.actions.github_issue_executor import (
    CreateGitHubIssueCommand,
    GitHubIssueExecutorOutcome,
    GitHubIssueExecutorResult,
)
from app.actions.github_issue_verifier import (
    GitHubIssueReadOutcome,
    GitHubIssueReadResult,
    GitHubIssueSearchResult,
    ObservedGitHubIssue,
)
from app.api.dependencies import (
    ACTION_VERIFICATION_UNAVAILABLE_DETAIL,
    get_database_session,
    get_github_issue_executor,
    get_github_issue_verifier,
)
from app.core.config import settings
from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.human_decisions import HumanDecisionType
from app.domain.signals import Evidence, Signal
from app.governance.contracts import HumanActorContext, HumanValidationCommand
from app.governance.human_validation import apply_human_validation
from app.infrastructure.database.action_execution_models import ActionExecutionModel
from app.infrastructure.database.action_verification_models import (
    ActionVerificationModel,
)
from app.infrastructure.database.candidate_persistence import persist_candidate
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.signal_persistence import persist_normalized_signal
from app.infrastructure.database.technical_debt_models import TechnicalDebtModel
from app.main import app
from app.signal_ingestion import NormalizedSignal

API_PATH = "/api/v1/technical-debts"
POC_ACTOR = "poc:local-reviewer"
TARGET_OWNER = "tdi-demo-target"
TARGET_NAME = "tdi-action-preview"
ISSUE_URL = "https://github.com/tdi-demo-target/tdi-action-preview/issues/42"
BASE_TIME = datetime(2026, 9, 7, 22, 0, tzinfo=UTC)
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class _ApiFakeExecutor:
    def __init__(self) -> None:
        self.commands: list[CreateGitHubIssueCommand] = []

    def create_issue(
        self,
        command: CreateGitHubIssueCommand,
    ) -> GitHubIssueExecutorResult:
        self.commands.append(command)
        return GitHubIssueExecutorResult(
            outcome=GitHubIssueExecutorOutcome.CREATED,
            external_issue_id=9001,
            external_issue_number=42,
            external_issue_url=ISSUE_URL,
        )


class _RejectingExecutor(_ApiFakeExecutor):
    def create_issue(
        self,
        command: CreateGitHubIssueCommand,
    ) -> GitHubIssueExecutorResult:
        self.commands.append(command)
        return GitHubIssueExecutorResult(outcome=GitHubIssueExecutorOutcome.REJECTED)


class _UnknownExecutor(_ApiFakeExecutor):
    def create_issue(
        self,
        command: CreateGitHubIssueCommand,
    ) -> GitHubIssueExecutorResult:
        self.commands.append(command)
        return GitHubIssueExecutorResult(
            outcome=GitHubIssueExecutorOutcome.TRANSPORT_UNKNOWN
        )


class _ApiFakeVerifier:
    def __init__(self, issue: ObservedGitHubIssue | None = None) -> None:
        self.issue = issue
        self.get_calls: list[tuple[str, str, int]] = []
        self.search_calls: list[tuple[str, str, str]] = []

    def get_issue(
        self,
        owner: str,
        repository: str,
        issue_number: int,
    ) -> GitHubIssueReadResult:
        self.get_calls.append((owner, repository, issue_number))
        assert self.issue is not None
        return GitHubIssueReadResult(
            outcome=GitHubIssueReadOutcome.FOUND,
            issue=self.issue,
        )

    def find_issues_by_marker(
        self,
        owner: str,
        repository: str,
        marker: str,
    ) -> GitHubIssueSearchResult:
        self.search_calls.append((owner, repository, marker))
        if self.issue is None:
            return GitHubIssueSearchResult(outcome=GitHubIssueReadOutcome.NOT_FOUND)
        return GitHubIssueSearchResult(
            outcome=GitHubIssueReadOutcome.FOUND,
            issues=(self.issue,),
        )


@pytest.fixture
def database_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(
        dbapi_connection: object,
        _connection_record: object,
    ) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]

    scripts = ScriptDirectory.from_config(Config(str(BACKEND_ROOT / "alembic.ini")))
    revisions = list(scripts.walk_revisions(base="base", head="heads"))
    with engine.begin() as connection:
        operations = Operations(MigrationContext.configure(connection))
        for revision in reversed(revisions):
            monkeypatch.setattr(revision.module, "op", operations, raising=False)
            revision.module.upgrade()

    with Session(engine) as session:
        seed_enterprise_estate(session)
        session.execute(
            text(
                "UPDATE incidents SET started_at = started_at || '+00:00' "
                "WHERE instr(started_at, '+') = 0"
            )
        )
        session.execute(
            text(
                "UPDATE incidents SET resolved_at = resolved_at || '+00:00' "
                "WHERE resolved_at IS NOT NULL AND instr(resolved_at, '+') = 0"
            )
        )
        session.commit()

    yield engine
    engine.dispose()


@pytest.fixture
def client(
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    monkeypatch.setattr(settings, "human_governance_enabled", False)
    monkeypatch.setattr(settings, "human_action_execution_enabled", True)
    monkeypatch.setattr(settings, "human_governance_actor_reference", POC_ACTOR)
    monkeypatch.setattr(settings, "github_issue_target_repository_owner", TARGET_OWNER)
    monkeypatch.setattr(settings, "github_issue_target_repository_name", TARGET_NAME)

    def override_database_session() -> Iterator[Session]:
        with Session(database_engine) as session:
            yield session

    app.dependency_overrides[get_database_session] = override_database_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _persist_candidate(engine: Engine, *, suffix: int) -> Candidate:
    evidence = Evidence(
        evidence_id=UUID(f"10000000-0000-0000-0000-{suffix:012d}"),
        source_system="action-verification-api-test",
        source_reference=f"evidence-{suffix}",
        captured_at=BASE_TIME + timedelta(minutes=suffix),
        reference_uri=f"https://synthetic.invalid/{suffix}",
    )
    signal = Signal(
        signal_id=UUID(f"00000000-0000-0000-0000-{suffix:012d}"),
        source_system="action-verification-api-test",
        source_record_id=f"source-{suffix}",
        detected_at=BASE_TIME + timedelta(minutes=suffix),
        signal_type="MISSING_TIMEOUT",
        affected_asset=CanonicalAssetRef(
            asset_key="svc-orbit-catalog",
            asset_type=AssetType.SERVICE,
        ),
        severity="MEDIUM",
        evidence_ids=frozenset({evidence.evidence_id}),
    )
    candidate = Candidate(
        candidate_id=UUID(f"20000000-0000-0000-0000-{suffix:012d}"),
        signal_ids=frozenset({signal.signal_id}),
        evidence_ids=frozenset({evidence.evidence_id}),
        canonical_asset=signal.affected_asset,
        hypothesis="Potential missing request timeout",
        correlation_rationale="Exact canonical asset and deterministic problem family.",
    )
    with Session(engine) as session:
        persist_normalized_signal(
            session,
            NormalizedSignal(signal=signal, evidence=frozenset({evidence})),
        )
        persist_candidate(session, candidate)
        session.commit()
    return candidate


def _register_technical_debt(engine: Engine, *, suffix: int) -> UUID:
    candidate = _persist_candidate(engine, suffix=suffix)
    with Session(engine) as session:
        created = apply_human_validation(
            session,
            HumanValidationCommand(
                candidate_id=candidate.candidate_id,
                decision=HumanDecisionType.VALIDATE,
                expected_governance_revision=0,
                rationale="The Candidate is a validated structural issue.",
            ),
            HumanActorContext(actor_reference=POC_ACTOR),
            clock=lambda: BASE_TIME + timedelta(minutes=suffix),
        )
    assert created.technical_debt is not None
    return created.technical_debt.technical_debt_id


def _prepare(client: TestClient, technical_debt_id: UUID) -> dict:
    response = client.post(f"{API_PATH}/{technical_debt_id}/action-proposals")
    assert response.status_code == 201
    return response.json()


def _approve(client: TestClient, technical_debt_id: UUID, proposal: dict) -> None:
    response = client.post(
        f"{API_PATH}/{technical_debt_id}/action-proposals/"
        f"{proposal['action_proposal_id']}/approvals",
        json={"expected_payload_fingerprint": proposal["payload_fingerprint"]},
    )
    assert response.status_code == 201


def _execute_path(technical_debt_id: UUID, action_proposal_id: str) -> str:
    return (
        f"{API_PATH}/{technical_debt_id}/action-proposals/"
        f"{action_proposal_id}/executions"
    )


def _verify_path(
    technical_debt_id: UUID,
    action_proposal_id: str,
    action_execution_id: str,
) -> str:
    return (
        f"{API_PATH}/{technical_debt_id}/action-proposals/"
        f"{action_proposal_id}/executions/{action_execution_id}/verifications"
    )


def _matching_issue(proposal: dict) -> ObservedGitHubIssue:
    return ObservedGitHubIssue(
        issue_id=9001,
        issue_number=42,
        html_url=ISSUE_URL,
        title=proposal["title"],
        body=proposal["body"],
        is_pull_request=False,
    )


def _succeed_execution(
    client: TestClient,
    technical_debt_id: UUID,
    proposal: dict,
) -> dict:
    _approve(client, technical_debt_id, proposal)
    executor = _ApiFakeExecutor()
    app.dependency_overrides[get_github_issue_executor] = lambda: executor
    response = client.post(
        _execute_path(technical_debt_id, proposal["action_proposal_id"])
    )
    assert response.status_code == 201
    return response.json()


def test_verification_request_body_is_422(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=1)
    proposal = _prepare(client, technical_debt_id)
    execution = _succeed_execution(client, technical_debt_id, proposal)

    response = client.post(
        _verify_path(
            technical_debt_id,
            proposal["action_proposal_id"],
            execution["action_execution_id"],
        ),
        json={
            "owner": "attacker",
            "repository": "other",
            "result": "PASS",
            "token": "secret",
        },
    )

    assert response.status_code == 422
    with Session(database_engine) as session:
        assert session.scalar(
            select(func.count()).select_from(ActionVerificationModel)
        ) == 0


def test_succeeded_read_back_returns_201_and_projects_on_detail(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=2)
    proposal = _prepare(client, technical_debt_id)
    execution = _succeed_execution(client, technical_debt_id, proposal)
    verifier = _ApiFakeVerifier(_matching_issue(proposal))
    app.dependency_overrides[get_github_issue_verifier] = lambda: verifier
    executor_calls_before = 1

    first = client.post(
        _verify_path(
            technical_debt_id,
            proposal["action_proposal_id"],
            execution["action_execution_id"],
        )
    )
    second = client.post(
        _verify_path(
            technical_debt_id,
            proposal["action_proposal_id"],
            execution["action_execution_id"],
        )
    )
    detail = client.get(f"{API_PATH}/{technical_debt_id}")

    assert first.status_code == 201
    assert first.json()["result"] == "PASS"
    assert first.json()["action_execution_id"] == execution["action_execution_id"]
    assert "token" not in first.json()
    assert "github_token" not in str(first.json()).lower()
    assert second.status_code == 201
    assert second.json()["action_verification_id"] != first.json()[
        "action_verification_id"
    ]
    assert detail.status_code == 200
    body = detail.json()
    assert body["lifecycle_status"] == "REGISTERED"
    assert [item["result"] for item in body["action_verifications"]] == ["PASS", "PASS"]
    assert verifier.get_calls == [
        (TARGET_OWNER, TARGET_NAME, 42),
        (TARGET_OWNER, TARGET_NAME, 42),
    ]
    assert verifier.search_calls == []
    with Session(database_engine) as session:
        executions = session.scalars(select(ActionExecutionModel)).all()
        assert len(executions) == executor_calls_before
        assert executions[0].status == "SUCCEEDED"


def test_failed_execution_verify_is_409(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=3)
    proposal = _prepare(client, technical_debt_id)
    _approve(client, technical_debt_id, proposal)
    app.dependency_overrides[get_github_issue_executor] = lambda: _RejectingExecutor()
    execution = client.post(
        _execute_path(technical_debt_id, proposal["action_proposal_id"])
    ).json()
    verifier = _ApiFakeVerifier(_matching_issue(proposal))
    app.dependency_overrides[get_github_issue_verifier] = lambda: verifier

    response = client.post(
        _verify_path(
            technical_debt_id,
            proposal["action_proposal_id"],
            execution["action_execution_id"],
        )
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "ActionExecution is not verifiable"}
    with Session(database_engine) as session:
        persisted = session.get(
            ActionExecutionModel, UUID(execution["action_execution_id"])
        )
        assert persisted is not None
        assert persisted.status == "FAILED"
        assert session.scalar(
            select(func.count()).select_from(ActionVerificationModel)
        ) == 0
    assert verifier.get_calls == []


def test_unknown_unresolved_is_409_and_does_not_post(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=4)
    proposal = _prepare(client, technical_debt_id)
    _approve(client, technical_debt_id, proposal)
    unknown_executor = _UnknownExecutor()
    app.dependency_overrides[get_github_issue_executor] = lambda: unknown_executor
    execution = client.post(
        _execute_path(technical_debt_id, proposal["action_proposal_id"])
    ).json()
    verifier = _ApiFakeVerifier(None)
    app.dependency_overrides[get_github_issue_verifier] = lambda: verifier

    response = client.post(
        _verify_path(
            technical_debt_id,
            proposal["action_proposal_id"],
            execution["action_execution_id"],
        )
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "External issue could not be reconciled"}
    assert len(unknown_executor.commands) == 1
    with Session(database_engine) as session:
        persisted = session.get(
            ActionExecutionModel, UUID(execution["action_execution_id"])
        )
        assert persisted is not None
        assert persisted.status == "UNKNOWN"


def test_missing_verifier_is_403(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=5)
    proposal = _prepare(client, technical_debt_id)
    execution = _succeed_execution(client, technical_debt_id, proposal)

    response = client.post(
        _verify_path(
            technical_debt_id,
            proposal["action_proposal_id"],
            execution["action_execution_id"],
        )
    )

    assert response.status_code == 403
    assert response.json() == {"detail": ACTION_VERIFICATION_UNAVAILABLE_DETAIL}


def test_missing_identities_are_404(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=6)
    proposal = _prepare(client, technical_debt_id)
    execution = _succeed_execution(client, technical_debt_id, proposal)
    verifier = _ApiFakeVerifier(_matching_issue(proposal))
    app.dependency_overrides[get_github_issue_verifier] = lambda: verifier

    missing_debt = client.post(
        _verify_path(
            uuid4(),
            proposal["action_proposal_id"],
            execution["action_execution_id"],
        )
    )
    missing_execution = client.post(
        _verify_path(
            technical_debt_id,
            proposal["action_proposal_id"],
            str(uuid4()),
        )
    )

    assert missing_debt.status_code == 404
    assert missing_debt.json() == {"detail": "TechnicalDebt not found"}
    assert missing_execution.status_code == 404
    assert missing_execution.json() == {"detail": "ActionExecution not found"}


def test_verification_does_not_close_technical_debt(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=7)
    proposal = _prepare(client, technical_debt_id)
    execution = _succeed_execution(client, technical_debt_id, proposal)
    app.dependency_overrides[get_github_issue_verifier] = lambda: _ApiFakeVerifier(
        _matching_issue(proposal)
    )

    client.post(
        _verify_path(
            technical_debt_id,
            proposal["action_proposal_id"],
            execution["action_execution_id"],
        )
    )

    with Session(database_engine) as session:
        debt = session.get(TechnicalDebtModel, technical_debt_id)
        assert debt is not None
        assert debt.lifecycle_status == "REGISTERED"


def test_github_write_executor_source_is_not_used_by_verifier() -> None:
    source = inspect.getsource(
        __import__("app.actions.verification", fromlist=["verify_action_execution"])
    )
    assert "create_issue" not in source
    assert "GitHubIssueExecutor" not in source
    assert "client.post" not in source
