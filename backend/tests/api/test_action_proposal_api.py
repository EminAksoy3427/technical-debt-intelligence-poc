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

from app.actions.contracts import (
    ActionProposalPersistenceConflict,
    ActionProposalSourceContextMissing,
    TechnicalDebtNotRegistered,
)
from app.actions.preparation import prepare_action_proposal
from app.api.dependencies import (
    ACTION_PREPARATION_UNAVAILABLE_DETAIL,
    get_action_preparation_session,
    get_database_session,
)
from app.api.v1 import technical_debts as technical_debts_module
from app.core.config import settings
from app.domain.action_proposals import (
    ActionType,
    action_proposal_reconciliation_marker,
    canonical_action_payload_fingerprint,
)
from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.human_decisions import HumanDecisionType
from app.domain.signals import Evidence, Signal
from app.governance.contracts import HumanActorContext, HumanValidationCommand
from app.governance.human_validation import apply_human_validation
from app.infrastructure.database.action_proposal_models import ActionProposalModel
from app.infrastructure.database.candidate_models import CandidateModel
from app.infrastructure.database.candidate_persistence import persist_candidate
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.signal_persistence import persist_normalized_signal
from app.main import app
from app.signal_ingestion import NormalizedSignal

API_PATH = "/api/v1/technical-debts"
CANDIDATES_PATH = "/api/v1/candidates"
POC_ACTOR = "poc:local-reviewer"
TARGET_OWNER = "tdi-demo-target"
TARGET_NAME = "tdi-action-preview"
BASE_TIME = datetime(2026, 9, 7, 16, 0, tzinfo=UTC)
FORBIDDEN_FIELDS = (
    "approved",
    "executed",
    "verification",
    "verified",
    "github_token",
    "risk",
    "effort",
    "priority",
    "validated_owner",
    "target_date",
)
CLIENT_INJECTED_FIELDS = (
    "action_type",
    "target_repository_owner",
    "target_repository_name",
    "repository",
    "title",
    "body",
    "payload_fingerprint",
    "reconciliation_marker",
    "prepared_by",
    "actor",
    "actor_reference",
    "approval",
    "effect",
    "risk",
    "scope",
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
        source_system="action-proposal-api-test",
        source_reference=f"evidence-{suffix}",
        captured_at=BASE_TIME + timedelta(minutes=suffix),
        reference_uri=f"https://synthetic.invalid/{suffix}",
    )
    signal = Signal(
        signal_id=UUID(f"00000000-0000-0000-0000-{suffix:012d}"),
        source_system="action-proposal-api-test",
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


def _prepare_path(technical_debt_id: UUID) -> str:
    return f"{API_PATH}/{technical_debt_id}/action-proposals"


def _proposal_count(engine: Engine, technical_debt_id: UUID) -> int:
    with Session(engine) as session:
        count = session.scalar(
            select(func.count())
            .select_from(ActionProposalModel)
            .where(ActionProposalModel.technical_debt_id == technical_debt_id)
        )
        return int(count or 0)


def test_prepare_returns_persisted_exact_proposal_truth(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=1)

    response = client.post(_prepare_path(technical_debt_id))

    assert response.status_code == 201
    body = response.json()
    assert body["technical_debt_id"] == str(technical_debt_id)
    assert body["action_type"] == ActionType.CREATE_GITHUB_ISSUE.value
    assert body["target_repository_owner"] == TARGET_OWNER
    assert body["target_repository_name"] == TARGET_NAME
    assert body["title"] == "Technical debt: svc-orbit-catalog"
    assert "Potential missing request timeout" in body["body"]
    assert body["prepared_by"] == POC_ACTOR
    proposal_id = UUID(body["action_proposal_id"])
    assert body["reconciliation_marker"] == action_proposal_reconciliation_marker(
        proposal_id
    )
    assert body["reconciliation_marker"] in body["body"]
    assert body["payload_fingerprint"] == canonical_action_payload_fingerprint(
        action_type=ActionType.CREATE_GITHUB_ISSUE.value,
        target_repository_owner=TARGET_OWNER,
        target_repository_name=TARGET_NAME,
        title=body["title"],
        body=body["body"],
    )
    assert _proposal_count(database_engine, technical_debt_id) == 1
    serialized = str(body).lower()
    assert all(field not in serialized for field in FORBIDDEN_FIELDS)


def test_prepare_does_not_require_a_request_body(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=2)

    response = client.post(_prepare_path(technical_debt_id))

    assert response.status_code == 201
    assert response.json()["technical_debt_id"] == str(technical_debt_id)


@pytest.mark.parametrize(
    ("extra_field", "suffix"),
    tuple((field, 30 + index) for index, field in enumerate(CLIENT_INJECTED_FIELDS)),
)
def test_prepare_rejects_client_injected_authority_fields(
    client: TestClient,
    database_engine: Engine,
    extra_field: str,
    suffix: int,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=suffix)

    response = client.post(
        _prepare_path(technical_debt_id),
        json={extra_field: "client-forged"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Request body is not supported"}
    assert _proposal_count(database_engine, technical_debt_id) == 0


def test_second_prepare_creates_another_immutable_proposal(
    client: TestClient,
    database_engine: Engine,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=4)

    first = client.post(_prepare_path(technical_debt_id))
    second = client.post(_prepare_path(technical_debt_id))

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["action_proposal_id"] != second.json()["action_proposal_id"]
    assert (
        first.json()["reconciliation_marker"] != second.json()["reconciliation_marker"]
    )
    assert _proposal_count(database_engine, technical_debt_id) == 2

    detail = client.get(f"{API_PATH}/{technical_debt_id}")

    assert detail.status_code == 200
    proposals = detail.json()["action_proposals"]
    assert [item["action_proposal_id"] for item in proposals] == [
        first.json()["action_proposal_id"],
        second.json()["action_proposal_id"],
    ]
    assert datetime.fromisoformat(
        proposals[0]["created_at"].replace("Z", "+00:00")
    ) <= datetime.fromisoformat(proposals[1]["created_at"].replace("Z", "+00:00"))
    assert "action_proposals" in detail.json()
    assert detail.json()["lifecycle_status"] == "REGISTERED"
    assert "source_candidate" in detail.json()
    assert "creation_human_decision" in detail.json()
    serialized = str(detail.json()).lower()
    assert all(field not in serialized for field in FORBIDDEN_FIELDS)


def test_missing_technical_debt_is_404(
    client: TestClient,
    database_engine: Engine,
) -> None:
    unknown = uuid4()

    response = client.post(_prepare_path(unknown))

    assert response.status_code == 404
    assert response.json() == {"detail": "TechnicalDebt not found"}
    assert _proposal_count(database_engine, unknown) == 0


def test_invalid_target_configuration_fails_closed(
    client: TestClient,
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=5)
    monkeypatch.setattr(settings, "github_issue_target_repository_owner", None)
    monkeypatch.setattr(settings, "github_issue_target_repository_name", None)

    response = client.post(_prepare_path(technical_debt_id))

    assert response.status_code == 503
    assert response.json() == {"detail": ACTION_PREPARATION_UNAVAILABLE_DETAIL}
    assert "GITHUB_ISSUE_TARGET" not in response.text
    assert _proposal_count(database_engine, technical_debt_id) == 0


def test_missing_actor_configuration_fails_closed(
    client: TestClient,
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=6)
    monkeypatch.setattr(settings, "human_governance_actor_reference", None)

    response = client.post(_prepare_path(technical_debt_id))

    assert response.status_code == 503
    assert response.json() == {"detail": ACTION_PREPARATION_UNAVAILABLE_DETAIL}
    assert _proposal_count(database_engine, technical_debt_id) == 0


def test_human_validation_remains_unavailable_when_disabled(
    client: TestClient,
    database_engine: Engine,
) -> None:
    candidate = _persist_candidate(database_engine, suffix=7)

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


def test_prepare_does_not_invoke_github_or_http(
    client: TestClient,
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=8)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Action preparation must not perform HTTP or GitHub calls")

    monkeypatch.setattr("httpx.Client", forbidden)
    monkeypatch.setattr("httpx.get", forbidden)
    monkeypatch.setattr("httpx.post", forbidden)

    response = client.post(_prepare_path(technical_debt_id))

    assert response.status_code == 201
    assert _proposal_count(database_engine, technical_debt_id) == 1


def test_action_proposal_api_has_no_github_write_or_token() -> None:
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
    assert "Verification" not in text


def test_github_read_connector_remains_get_only() -> None:
    source = inspect.getsource(
        importlib.import_module("app.infrastructure.github_issues")
    )

    assert "client.get(" in source
    assert "client.post(" not in source
    assert "client.put(" not in source
    assert "client.patch(" not in source
    assert "client.delete(" not in source
    assert "httpx.post" not in source
    assert "GITHUB_TOKEN" not in source


def test_unregistered_technical_debt_is_409(
    client: TestClient,
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=9)

    def raise_unregistered(*_args: object, **_kwargs: object) -> None:
        raise TechnicalDebtNotRegistered("TechnicalDebt is not REGISTERED")

    monkeypatch.setattr(
        "app.api.v1.technical_debts.prepare_action_proposal",
        raise_unregistered,
    )

    response = client.post(_prepare_path(technical_debt_id))

    assert response.status_code == 409
    assert response.json() == {"detail": "TechnicalDebt is not REGISTERED"}
    assert _proposal_count(database_engine, technical_debt_id) == 0


def test_source_context_missing_is_integrity_500(
    client: TestClient,
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=10)

    def raise_missing(*_args: object, **_kwargs: object) -> None:
        raise ActionProposalSourceContextMissing(
            "TechnicalDebt source Candidate is unexpectedly missing"
        )

    monkeypatch.setattr(
        "app.api.v1.technical_debts.prepare_action_proposal",
        raise_missing,
    )

    response = client.post(_prepare_path(technical_debt_id))

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Persisted TechnicalDebt data failed integrity validation"
    }


def test_persistence_conflict_is_409(
    client: TestClient,
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=11)

    def raise_conflict(*_args: object, **_kwargs: object) -> None:
        raise ActionProposalPersistenceConflict(
            "An ActionProposal already exists for this reconciliation marker"
        )

    monkeypatch.setattr(
        "app.api.v1.technical_debts.prepare_action_proposal",
        raise_conflict,
    )

    response = client.post(_prepare_path(technical_debt_id))

    assert response.status_code == 409
    assert response.json() == {
        "detail": "ActionProposal could not be persisted because of a conflict"
    }


def test_route_invokes_prepare_with_transaction_free_session(
    client: TestClient,
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    technical_debt_id = _register_technical_debt(database_engine, suffix=12)
    seen: dict[str, bool] = {}
    original = prepare_action_proposal

    def capture(
        session: Session,
        command: object,
        actor_context: object,
        preparation_context: object,
        **kwargs: object,
    ) -> object:
        seen["in_transaction"] = session.in_transaction()
        return original(
            session,
            command,
            actor_context,
            preparation_context,
            **kwargs,
        )

    monkeypatch.setattr("app.api.v1.technical_debts.prepare_action_proposal", capture)

    response = client.post(_prepare_path(technical_debt_id))

    assert response.status_code == 201
    assert seen["in_transaction"] is False


def test_action_preparation_session_guard_rejects_open_transaction(
    database_engine: Engine,
) -> None:
    candidate_id = _persist_candidate(database_engine, suffix=13).candidate_id

    with Session(database_engine) as session:
        session.get(CandidateModel, candidate_id)
        assert session.in_transaction()
        with pytest.raises(RuntimeError, match="transaction-free Session"):
            get_action_preparation_session(session)
