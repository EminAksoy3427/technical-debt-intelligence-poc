import ast
import importlib
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

from app.actions.approval import approve_action_proposal
from app.actions.github_issue_executor import (
    CreateGitHubIssueCommand,
    GitHubIssueExecutorOutcome,
    GitHubIssueExecutorResult,
)
from app.api.dependencies import (
    ACTION_APPROVAL_UNAVAILABLE_DETAIL,
    get_action_approval_session,
    get_database_session,
    get_github_issue_executor,
)
from app.api.v1 import technical_debts as technical_debts_module
from app.core.config import settings
from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.human_decisions import HumanDecisionType
from app.domain.signals import Evidence, Signal
from app.governance.contracts import HumanActorContext, HumanValidationCommand
from app.governance.human_validation import apply_human_validation
from app.infrastructure.database.action_approval_models import ActionApprovalModel
from app.infrastructure.database.action_execution_models import ActionExecutionModel
from app.infrastructure.database.action_policy_models import ActionPolicyDecisionModel
from app.infrastructure.database.action_proposal_models import ActionProposalModel
from app.infrastructure.database.candidate_models import CandidateModel
from app.infrastructure.database.candidate_persistence import persist_candidate
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.signal_persistence import persist_normalized_signal
from app.infrastructure.database.technical_debt_models import TechnicalDebtModel
from app.main import app
from app.signal_ingestion import NormalizedSignal

API_PATH = "/api/v1/technical-debts"
CANDIDATES_PATH = "/api/v1/candidates"
POC_ACTOR = "poc:local-reviewer"
TARGET_OWNER = "tdi-demo-target"
TARGET_NAME = "tdi-action-preview"
BASE_TIME = datetime(2026, 9, 7, 16, 0, tzinfo=UTC)
CLIENT_INJECTED_FIELDS = (
    "actor_reference",
    "approved",
    "repository",
    "title",
    "body",
    "action_type",
    "effect",
    "risk",
    "scope",
    "policy",
    "execution",
)
BACKEND_ROOT = Path(__file__).resolve().parents[2]


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
        source_system="action-approval-api-test",
        source_reference=f"evidence-{suffix}",
        captured_at=BASE_TIME + timedelta(minutes=suffix),
        reference_uri=f"https://synthetic.invalid/{suffix}",
    )
    signal = Signal(
        signal_id=UUID(f"00000000-0000-0000-0000-{suffix:012d}"),
        source_system="action-approval-api-test",
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


def _approve_path(technical_debt_id: UUID, action_proposal_id: str) -> str:
    return (
        f"{API_PATH}/{technical_debt_id}/action-proposals/"
        f"{action_proposal_id}/approvals"
    )


def _execution_path(technical_debt_id: UUID, action_proposal_id: str) -> str:
    return (
        f"{API_PATH}/{technical_debt_id}/action-proposals/"
        f"{action_proposal_id}/executions"
    )


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
            external_issue_url="https://github.example/issues/42",
        )


def _approval_count(engine: Engine) -> int:
    with Session(engine) as session:
        count = session.scalar(select(func.count()).select_from(ActionApprovalModel))
        return int(count or 0)


def test_valid_fingerprint_returns_201_approval(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=1)
    proposal = _prepare(client, technical_debt_id)

    response = client.post(
        _approve_path(technical_debt_id, proposal["action_proposal_id"]),
        json={"expected_payload_fingerprint": proposal["payload_fingerprint"]},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["action_proposal_id"] == proposal["action_proposal_id"]
    assert body["payload_fingerprint"] == proposal["payload_fingerprint"]
    assert body["actor_reference"] == POC_ACTOR
    assert "approved" not in body
    assert _approval_count(database_engine) == 1


def test_stale_fingerprint_is_409_with_zero_approvals(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=2)
    proposal = _prepare(client, technical_debt_id)
    stale = ("0" if proposal["payload_fingerprint"][0] != "0" else "1") + proposal[
        "payload_fingerprint"
    ][1:]

    response = client.post(
        _approve_path(technical_debt_id, proposal["action_proposal_id"]),
        json={"expected_payload_fingerprint": stale},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "expected_payload_fingerprint does not match the persisted ActionProposal"
        )
    }
    assert _approval_count(database_engine) == 0


def test_same_proposal_second_approval_is_409(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=3)
    proposal = _prepare(client, technical_debt_id)
    first = client.post(
        _approve_path(technical_debt_id, proposal["action_proposal_id"]),
        json={"expected_payload_fingerprint": proposal["payload_fingerprint"]},
    )
    second = client.post(
        _approve_path(technical_debt_id, proposal["action_proposal_id"]),
        json={"expected_payload_fingerprint": proposal["payload_fingerprint"]},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json() == {"detail": "ActionProposal is already approved"}
    assert _approval_count(database_engine) == 1


def test_competing_proposal_approval_is_409(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=4)
    first_proposal = _prepare(client, technical_debt_id)
    second_proposal = _prepare(client, technical_debt_id)
    first = client.post(
        _approve_path(technical_debt_id, first_proposal["action_proposal_id"]),
        json={"expected_payload_fingerprint": first_proposal["payload_fingerprint"]},
    )
    competing = client.post(
        _approve_path(technical_debt_id, second_proposal["action_proposal_id"]),
        json={"expected_payload_fingerprint": second_proposal["payload_fingerprint"]},
    )

    assert first.status_code == 201
    assert competing.status_code == 409
    assert competing.json() == {
        "detail": (
            "A competing ActionProposal already holds approval for this logical action"
        )
    }
    assert _approval_count(database_engine) == 1


def test_detail_projects_approvals_with_empty_execution_history(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=5)
    proposal = _prepare(client, technical_debt_id)
    approval = client.post(
        _approve_path(technical_debt_id, proposal["action_proposal_id"]),
        json={"expected_payload_fingerprint": proposal["payload_fingerprint"]},
    ).json()

    detail = client.get(f"{API_PATH}/{technical_debt_id}")

    assert detail.status_code == 200
    body = detail.json()
    assert [item["action_proposal_id"] for item in body["action_proposals"]] == [
        proposal["action_proposal_id"]
    ]
    assert [item["action_approval_id"] for item in body["action_approvals"]] == [
        approval["action_approval_id"]
    ]
    assert body["action_approvals"][0]["payload_fingerprint"] == (
        proposal["payload_fingerprint"]
    )
    assert body["lifecycle_status"] == "REGISTERED"
    serialized = str(body).lower()
    assert body["action_executions"] == []
    assert body["action_verifications"] == []
    assert "github_token" not in serialized
    assert "approved" not in serialized


def test_human_governance_enabled_does_not_enable_approval(
    client: TestClient,
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=6)
    proposal = _prepare(client, technical_debt_id)
    monkeypatch.setattr(settings, "human_governance_enabled", True)
    monkeypatch.setattr(settings, "human_action_execution_enabled", False)

    response = client.post(
        _approve_path(technical_debt_id, proposal["action_proposal_id"]),
        json={"expected_payload_fingerprint": proposal["payload_fingerprint"]},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": ACTION_APPROVAL_UNAVAILABLE_DETAIL}
    assert _approval_count(database_engine) == 0


def test_execution_flag_false_is_403(
    client: TestClient,
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=7)
    proposal = _prepare(client, technical_debt_id)
    monkeypatch.setattr(settings, "human_action_execution_enabled", False)

    response = client.post(
        _approve_path(technical_debt_id, proposal["action_proposal_id"]),
        json={"expected_payload_fingerprint": proposal["payload_fingerprint"]},
    )

    assert response.status_code == 403
    assert _approval_count(database_engine) == 0


def test_human_validation_remains_unavailable_when_only_execution_is_enabled(
    client: TestClient,
    database_engine: Engine,
) -> None:
    candidate = _persist_candidate(database_engine, suffix=8)

    response = client.post(
        f"{CANDIDATES_PATH}/{candidate.candidate_id}/human-decisions",
        json={
            "decision": "VALIDATE",
            "rationale": "The Candidate is a validated structural issue.",
            "expected_governance_revision": 0,
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Human Validation is not available"}


def test_extra_request_fields_are_422(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=9)
    proposal = _prepare(client, technical_debt_id)

    response = client.post(
        _approve_path(technical_debt_id, proposal["action_proposal_id"]),
        json={
            "expected_payload_fingerprint": proposal["payload_fingerprint"],
            "actor_reference": "poc:forged",
        },
    )

    assert response.status_code == 422
    assert _approval_count(database_engine) == 0


@pytest.mark.parametrize(
    ("extra_field", "suffix"),
    tuple((field, 40 + index) for index, field in enumerate(CLIENT_INJECTED_FIELDS)),
)
def test_client_cannot_inject_authority_fields(
    client: TestClient,
    database_engine: Engine,
    extra_field: str,
    suffix: int,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=suffix)
    proposal = _prepare(client, technical_debt_id)

    response = client.post(
        _approve_path(technical_debt_id, proposal["action_proposal_id"]),
        json={
            "expected_payload_fingerprint": proposal["payload_fingerprint"],
            extra_field: "client-forged",
        },
    )

    assert response.status_code == 422
    assert _approval_count(database_engine) == 0


def test_missing_technical_debt_is_404(
    client: TestClient,
    database_engine: Engine,
) -> None:
    response = client.post(
        _approve_path(uuid4(), str(uuid4())),
        json={"expected_payload_fingerprint": "a" * 64},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "TechnicalDebt not found"}
    assert _approval_count(database_engine) == 0


def test_missing_proposal_is_404(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=10)

    response = client.post(
        _approve_path(technical_debt_id, str(uuid4())),
        json={"expected_payload_fingerprint": "a" * 64},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "ActionProposal not found"}


def test_proposal_on_other_technical_debt_is_404(
    client: TestClient,
    database_engine: Engine,
) -> None:
    first_debt = _register_technical_debt(database_engine, suffix=11)
    second_debt = _register_technical_debt(database_engine, suffix=12)
    proposal = _prepare(client, first_debt)

    response = client.post(
        _approve_path(second_debt, proposal["action_proposal_id"]),
        json={"expected_payload_fingerprint": proposal["payload_fingerprint"]},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "ActionProposal not found"}
    assert _approval_count(database_engine) == 0


def test_runtime_missing_actor_fails_closed_without_persisting(
    client: TestClient,
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prove the dependency fails closed if actor is cleared at runtime.

    Normal invalid startup (HUMAN_ACTION_EXECUTION_ENABLED=true without an
    actor) is rejected by Settings validation and does not reach this endpoint.
    """
    technical_debt_id = _register_technical_debt(database_engine, suffix=13)
    proposal = _prepare(client, technical_debt_id)
    monkeypatch.setattr(settings, "human_governance_actor_reference", None)

    response = client.post(
        _approve_path(technical_debt_id, proposal["action_proposal_id"]),
        json={"expected_payload_fingerprint": proposal["payload_fingerprint"]},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": ACTION_APPROVAL_UNAVAILABLE_DETAIL}
    assert "HUMAN_" not in response.text
    assert _approval_count(database_engine) == 0


def test_approve_does_not_invoke_github_or_http(
    client: TestClient,
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=14)
    proposal = _prepare(client, technical_debt_id)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Action approval must not perform HTTP or GitHub calls")

    monkeypatch.setattr("httpx.Client", forbidden)
    monkeypatch.setattr("httpx.get", forbidden)
    monkeypatch.setattr("httpx.post", forbidden)

    response = client.post(
        _approve_path(technical_debt_id, proposal["action_proposal_id"]),
        json={"expected_payload_fingerprint": proposal["payload_fingerprint"]},
    )

    assert response.status_code == 201


def test_approval_api_does_not_own_github_transport_or_token() -> None:
    source_path = Path(inspect.getsourcefile(technical_debts_module) or "")
    text = source_path.read_text(encoding="utf-8")
    module = ast.parse(text, filename=str(source_path))
    imported: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)

    assert not any(
        name == prefix or name.startswith(f"{prefix}.")
        for name in imported
        for prefix in (
            "httpx",
            "app.infrastructure.github_issues",
            "app.connectors.github_issues",
        )
    )
    assert "GITHUB_TOKEN" not in text
    assert "github_token" not in text
    assert "Authorization" not in text
    assert "evaluate_candidate_tool_policy" not in text


def test_execution_api_persists_policy_deny_without_approval(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=31)
    proposal = _prepare(client, technical_debt_id)

    response = client.post(
        _execution_path(technical_debt_id, proposal["action_proposal_id"])
    )

    assert response.status_code == 403
    with Session(database_engine) as session:
        assert session.scalar(
            select(func.count()).select_from(ActionPolicyDecisionModel)
        ) == 1
        assert session.scalar(
            select(func.count()).select_from(ActionExecutionModel)
        ) == 0


def test_execution_api_missing_token_denies_approved_proposal(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=32)
    proposal = _prepare(client, technical_debt_id)
    approval = client.post(
        _approve_path(technical_debt_id, proposal["action_proposal_id"]),
        json={"expected_payload_fingerprint": proposal["payload_fingerprint"]},
    )
    assert approval.status_code == 201

    response = client.post(
        _execution_path(technical_debt_id, proposal["action_proposal_id"])
    )

    assert response.status_code == 403
    with Session(database_engine) as session:
        decision = session.scalar(select(ActionPolicyDecisionModel))
        assert decision is not None
        assert decision.reason_code == "EXECUTION_DISABLED"


def test_execution_api_creates_once_then_returns_existing(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=33)
    proposal = _prepare(client, technical_debt_id)
    approval = client.post(
        _approve_path(technical_debt_id, proposal["action_proposal_id"]),
        json={"expected_payload_fingerprint": proposal["payload_fingerprint"]},
    )
    assert approval.status_code == 201
    executor = _ApiFakeExecutor()
    app.dependency_overrides[get_github_issue_executor] = lambda: executor

    first = client.post(
        _execution_path(technical_debt_id, proposal["action_proposal_id"])
    )
    duplicate = client.post(
        _execution_path(technical_debt_id, proposal["action_proposal_id"])
    )

    assert first.status_code == 201
    assert first.json()["status"] == "SUCCEEDED"
    assert duplicate.status_code == 200
    assert duplicate.json() == first.json()
    assert executor.commands == [
        CreateGitHubIssueCommand(
            owner=TARGET_OWNER,
            repository=TARGET_NAME,
            title=proposal["title"],
            body=proposal["body"],
        )
    ]


def test_execution_api_rejects_any_client_mutation_body(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=34)
    proposal = _prepare(client, technical_debt_id)

    response = client.post(
        _execution_path(technical_debt_id, proposal["action_proposal_id"]),
        json={
            "repository": "attacker/repository",
            "title": "injected",
            "body": "injected",
            "status": "SUCCEEDED",
            "token": "secret",
        },
    )

    assert response.status_code == 422


def test_github_read_connector_remains_get_only() -> None:
    source = inspect.getsource(
        importlib.import_module("app.infrastructure.github_issues")
    )

    assert "client.get(" in source
    assert "client.post(" not in source
    assert "GITHUB_TOKEN" not in source


def test_route_invokes_approve_with_transaction_free_session(
    client: TestClient,
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=15)
    proposal = _prepare(client, technical_debt_id)
    seen: dict[str, bool] = {}
    original = approve_action_proposal

    def capture(
        session: Session,
        command: object,
        actor_context: object,
        **kwargs: object,
    ) -> object:
        seen["in_transaction"] = session.in_transaction()
        return original(session, command, actor_context, **kwargs)

    monkeypatch.setattr("app.api.v1.technical_debts.approve_action_proposal", capture)

    response = client.post(
        _approve_path(technical_debt_id, proposal["action_proposal_id"]),
        json={"expected_payload_fingerprint": proposal["payload_fingerprint"]},
    )

    assert response.status_code == 201
    assert seen["in_transaction"] is False


def test_action_approval_session_guard_rejects_open_transaction(
    database_engine: Engine,
) -> None:
    candidate_id = _persist_candidate(database_engine, suffix=16).candidate_id

    with Session(database_engine) as session:
        session.get(CandidateModel, candidate_id)
        assert session.in_transaction()
        with pytest.raises(RuntimeError, match="transaction-free Session"):
            get_action_approval_session(session)


def test_approval_does_not_mutate_proposal_or_debt_rows(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=17)
    proposal = _prepare(client, technical_debt_id)
    with Session(database_engine) as session:
        before_proposal = session.get(
            ActionProposalModel,
            UUID(proposal["action_proposal_id"]),
        )
        before_debt = session.get(TechnicalDebtModel, technical_debt_id)
        assert before_proposal is not None
        assert before_debt is not None
        before_title = before_proposal.title
        before_body = before_proposal.body
        before_status = before_debt.lifecycle_status

    response = client.post(
        _approve_path(technical_debt_id, proposal["action_proposal_id"]),
        json={"expected_payload_fingerprint": proposal["payload_fingerprint"]},
    )

    assert response.status_code == 201
    with Session(database_engine) as session:
        after_proposal = session.get(
            ActionProposalModel,
            UUID(proposal["action_proposal_id"]),
        )
        after_debt = session.get(TechnicalDebtModel, technical_debt_id)
        assert after_proposal is not None
        assert after_debt is not None
        assert after_proposal.title == before_title
        assert after_proposal.body == before_body
        assert after_debt.lifecycle_status == before_status
