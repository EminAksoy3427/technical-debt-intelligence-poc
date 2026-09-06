from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.agent.composition import build_candidate_tool_registry
from app.api.dependencies import get_database_session, get_human_validation_session
from app.core.config import settings
from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.human_decisions import HumanDecisionType
from app.domain.signals import Evidence, Signal
from app.governance.human_validation import apply_human_validation
from app.infrastructure.database.candidate_models import CandidateModel
from app.infrastructure.database.candidate_persistence import persist_candidate
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.human_decision_models import HumanDecisionModel
from app.infrastructure.database.signal_persistence import persist_normalized_signal
from app.infrastructure.database.technical_debt_models import TechnicalDebtModel
from app.main import app
from app.signal_ingestion import NormalizedSignal

API_PATH = "/api/v1/candidates"
POC_ACTOR = "poc:local-reviewer"
BASE_TIME = datetime(2026, 9, 6, 18, 0, tzinfo=UTC)
CANDIDATE_ID = UUID("20000000-0000-0000-0000-000000000801")


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

    backend_root = Path(__file__).resolve().parents[2]
    scripts = ScriptDirectory.from_config(Config(str(backend_root / "alembic.ini")))
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
    monkeypatch.setattr(settings, "human_governance_enabled", True)
    monkeypatch.setattr(settings, "human_governance_actor_reference", POC_ACTOR)

    def override_database_session() -> Iterator[Session]:
        with Session(database_engine) as session:
            yield session

    app.dependency_overrides[get_database_session] = override_database_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _persist_candidate(engine: Engine, candidate_id: UUID = CANDIDATE_ID) -> Candidate:
    evidence = Evidence(
        evidence_id=UUID("10000000-0000-0000-0000-000000000801"),
        source_system="human-decision-api-test",
        source_reference="evidence-801",
        captured_at=BASE_TIME + timedelta(minutes=1),
        reference_uri="https://synthetic.invalid/801",
    )
    signal = Signal(
        signal_id=UUID("00000000-0000-0000-0000-000000000801"),
        source_system="human-decision-api-test",
        source_record_id="source-801",
        detected_at=BASE_TIME,
        signal_type="MISSING_TIMEOUT",
        affected_asset=CanonicalAssetRef(
            asset_key="svc-orbit-catalog",
            asset_type=AssetType.SERVICE,
        ),
        severity="MEDIUM",
        evidence_ids=frozenset({evidence.evidence_id}),
    )
    candidate = Candidate(
        candidate_id=candidate_id,
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


def _post_path(candidate_id: UUID = CANDIDATE_ID) -> str:
    return f"{API_PATH}/{candidate_id}/human-decisions"


def _validate_payload(revision: int = 0) -> dict[str, object]:
    return {
        "decision": "VALIDATE",
        "rationale": "The Candidate is a validated structural issue.",
        "expected_governance_revision": revision,
    }


def _reject_payload(revision: int = 0) -> dict[str, object]:
    return {
        "decision": "REJECT",
        "rationale": "The findings do not form a structural issue.",
        "expected_governance_revision": revision,
    }


def _request_info_payload(revision: int = 0) -> dict[str, object]:
    return {
        "decision": "REQUEST_INFO",
        "requested_information": "Who owns the catalog service?",
        "expected_governance_revision": revision,
    }


def _counts(engine: Engine, candidate_id: UUID = CANDIDATE_ID) -> tuple[int, int]:
    with Session(engine) as session:
        decisions = session.scalar(
            select(func.count())
            .select_from(HumanDecisionModel)
            .where(HumanDecisionModel.candidate_id == candidate_id)
        )
        debts = session.scalar(
            select(func.count())
            .select_from(TechnicalDebtModel)
            .where(TechnicalDebtModel.source_candidate_id == candidate_id)
        )
        return int(decisions or 0), int(debts or 0)


def test_validate_creates_persisted_decision_and_technical_debt(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)

    response = client.post(_post_path(), json=_validate_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["human_decision"]["candidate_id"] == str(CANDIDATE_ID)
    assert body["human_decision"]["sequence_number"] == 1
    assert body["human_decision"]["decision"] == "VALIDATE"
    assert body["human_decision"]["actor_reference"] == POC_ACTOR
    assert body["governance"] == {"state": "VALIDATED", "revision": 1}
    assert body["technical_debt"]["lifecycle_status"] == "REGISTERED"
    assert body["technical_debt"]["source_candidate_id"] == str(CANDIDATE_ID)
    assert _counts(database_engine) == (1, 1)


def test_reject_persists_decision_without_technical_debt(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)

    response = client.post(_post_path(), json=_reject_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["human_decision"]["decision"] == "REJECT"
    assert body["governance"] == {"state": "REJECTED", "revision": 1}
    assert body["technical_debt"] is None
    assert _counts(database_engine) == (1, 0)


def test_request_info_persists_decision_without_technical_debt(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)

    response = client.post(_post_path(), json=_request_info_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["human_decision"]["decision"] == "REQUEST_INFO"
    assert body["governance"] == {"state": "INFORMATION_REQUESTED", "revision": 1}
    assert body["technical_debt"] is None
    assert _counts(database_engine) == (1, 0)


def test_request_info_then_validate_honors_revisions_and_creates_one_debt(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)

    first = client.post(_post_path(), json=_request_info_payload())
    second = client.post(_post_path(), json=_validate_payload(revision=1))

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["human_decision"]["sequence_number"] == 2
    assert second.json()["governance"] == {"state": "VALIDATED", "revision": 2}
    assert second.json()["technical_debt"] is not None
    assert _counts(database_engine) == (2, 1)


def test_refresh_reconstructs_validate_governance_and_technical_debt(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)

    created = client.post(_post_path(), json=_validate_payload())
    refreshed = client.get(f"{API_PATH}/{CANDIDATE_ID}")

    assert created.status_code == 201
    assert refreshed.status_code == 200
    created_body = created.json()
    governance = refreshed.json()["governance"]
    assert governance["state"] == created_body["governance"]["state"]
    assert governance["revision"] == created_body["governance"]["revision"]
    assert [item["human_decision_id"] for item in governance["decisions"]] == [
        created_body["human_decision"]["human_decision_id"]
    ]
    assert governance["technical_debt"] == created_body["technical_debt"]


def test_refresh_reconstructs_request_info_governance(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)

    created = client.post(_post_path(), json=_request_info_payload())
    refreshed = client.get(f"{API_PATH}/{CANDIDATE_ID}")

    assert created.status_code == 201
    assert refreshed.status_code == 200
    governance = refreshed.json()["governance"]
    assert governance["state"] == "INFORMATION_REQUESTED"
    assert governance["revision"] == 1
    assert governance["decisions"][0]["decision"] == "REQUEST_INFO"
    assert governance["technical_debt"] is None


def test_refresh_reconstructs_reject_governance(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)

    created = client.post(_post_path(), json=_reject_payload())
    refreshed = client.get(f"{API_PATH}/{CANDIDATE_ID}")

    assert created.status_code == 201
    governance = refreshed.json()["governance"]
    assert governance["state"] == "REJECTED"
    assert governance["revision"] == 1
    assert governance["technical_debt"] is None


def test_missing_candidate_is_404(
    client: TestClient,
    database_engine: Engine,
) -> None:
    unknown = UUID("30000000-0000-0000-0000-000000000801")

    response = client.post(_post_path(unknown), json=_validate_payload())

    assert response.status_code == 404
    assert response.json() == {"detail": "Candidate not found"}
    assert _counts(database_engine, unknown) == (0, 0)


def test_stale_revision_is_409(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)
    first = client.post(_post_path(), json=_request_info_payload())

    response = client.post(_post_path(), json=_validate_payload(revision=0))

    assert first.status_code == 201
    assert response.status_code == 409
    assert "expected_governance_revision" in response.json()["detail"]
    assert _counts(database_engine) == (1, 0)


def test_terminal_state_invalid_transition_is_409(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)
    first = client.post(_post_path(), json=_validate_payload())

    response = client.post(_post_path(), json=_reject_payload(revision=1))

    assert first.status_code == 201
    assert response.status_code == 409
    assert "not a legal transition" in response.json()["detail"]
    assert _counts(database_engine) == (1, 1)


def test_invalid_conditional_decision_content_is_422(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)

    response = client.post(
        _post_path(),
        json={
            "decision": "VALIDATE",
            "expected_governance_revision": 0,
        },
    )

    assert response.status_code == 422
    assert "rationale" in response.json()["detail"]
    assert _counts(database_engine) == (0, 0)


def test_negative_revision_is_422(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)

    response = client.post(
        _post_path(),
        json={
            "decision": "VALIDATE",
            "rationale": "The Candidate is a validated structural issue.",
            "expected_governance_revision": -1,
        },
    )

    assert response.status_code == 422
    assert _counts(database_engine) == (0, 0)


def test_unsupported_decision_is_422(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)

    response = client.post(
        _post_path(),
        json={
            "decision": "APPROVE",
            "rationale": "Not a supported decision.",
            "expected_governance_revision": 0,
        },
    )

    assert response.status_code == 422
    assert _counts(database_engine) == (0, 0)


def test_malformed_candidate_uuid_is_422(client: TestClient) -> None:
    response = client.post(
        f"{API_PATH}/not-a-uuid/human-decisions",
        json=_validate_payload(),
    )

    assert response.status_code == 422


def test_disabled_governance_is_403(
    client: TestClient,
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "human_governance_enabled", False)
    _persist_candidate(database_engine)

    response = client.post(_post_path(), json=_validate_payload())

    assert response.status_code == 403
    assert response.json() == {"detail": "Human Validation is not available"}
    assert _counts(database_engine) == (0, 0)


@pytest.mark.parametrize(
    "extra_field",
    (
        "actor_reference",
        "role",
        "approval",
        "authorization",
        "is_authorized",
        "provider",
        "model",
        "tool",
        "technical_debt_id",
    ),
)
def test_authority_extra_fields_are_rejected(
    client: TestClient,
    database_engine: Engine,
    extra_field: str,
) -> None:
    _persist_candidate(database_engine)
    payload = _validate_payload()
    payload[extra_field] = "client-forged"

    response = client.post(_post_path(), json=payload)

    assert response.status_code == 422
    assert _counts(database_engine) == (0, 0)


def test_configured_server_actor_is_persisted_not_client_identity(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)

    response = client.post(_post_path(), json=_validate_payload())

    assert response.status_code == 201
    assert response.json()["human_decision"]["actor_reference"] == POC_ACTOR
    with Session(database_engine) as session:
        persisted = session.scalar(select(HumanDecisionModel))
        assert persisted is not None
        assert persisted.actor_reference == POC_ACTOR


def test_human_validation_is_not_an_agent_tool() -> None:
    class _UnusedReader:
        def read_candidate_evidence(self, candidate_id: object) -> None:
            raise AssertionError("Human Validation must not execute Agent tools")

        def read_candidate_dependency_context(self, candidate_id: object) -> None:
            raise AssertionError("Human Validation must not execute Agent tools")

        def read_candidate_enterprise_context(self, candidate_id: object) -> None:
            raise AssertionError("Human Validation must not execute Agent tools")

    tool_ids = {
        item.descriptor.tool_id
        for item in build_candidate_tool_registry(_UnusedReader()).list()  # type: ignore[arg-type]
    }

    assert tool_ids.isdisjoint(
        {
            "human_validation",
            "human_decision",
            "validate_candidate",
            "reject_candidate",
            "request_info",
            *{item.lower() for item in HumanDecisionType},
        }
    )


def test_route_invokes_human_validation_with_transaction_free_session(
    client: TestClient,
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _persist_candidate(database_engine)
    seen: dict[str, bool] = {}
    original = apply_human_validation

    def capture(
        session: Session,
        command: object,
        actor_context: object,
        **kwargs: object,
    ) -> object:
        seen["in_transaction"] = session.in_transaction()
        return original(session, command, actor_context, **kwargs)

    monkeypatch.setattr(
        "app.api.v1.human_decisions.apply_human_validation",
        capture,
    )

    response = client.post(_post_path(), json=_validate_payload())

    assert response.status_code == 201
    assert seen["in_transaction"] is False


def test_human_validation_session_guard_rejects_open_transaction(
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)

    with Session(database_engine) as session:
        session.get(CandidateModel, CANDIDATE_ID)
        assert session.in_transaction()
        with pytest.raises(RuntimeError, match="transaction-free Session"):
            get_human_validation_session(session)
