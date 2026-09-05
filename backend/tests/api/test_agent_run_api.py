from collections.abc import Iterator
from datetime import UTC, datetime
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

from app.agent.audit_contracts import (
    AgentRunStopReason,
    AssessmentOutcome,
    StructuredAssessment,
)
from app.agent.runtime_contracts import FinalAssessmentDecision, ToolCallRequest
from app.agent.scripted_provider import ScriptedInvestigationProvider
from app.api.dependencies import (
    get_candidate_investigation_provider,
    get_database_session,
)
from app.infrastructure.database.agent_audit_models import (
    AgentRunModel,
    PolicyDecisionModel,
    ToolExecutionModel,
)
from app.infrastructure.database.candidate_models import (
    CandidateModel,
    CandidateSignalModel,
)
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel
from app.main import app

API_PATH = "/api/v1/candidates"
BASE_TIME = datetime(2026, 9, 5, 10, 0, tzinfo=UTC)
CANDIDATE_ID = UUID("20000000-0000-0000-0000-000000000501")
OTHER_CANDIDATE_ID = UUID("20000000-0000-0000-0000-000000000502")
EVIDENCE_ID = UUID("10000000-0000-0000-0000-000000000501")


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
def client(database_engine: Engine) -> Iterator[TestClient]:
    def override_database_session() -> Iterator[Session]:
        with Session(database_engine) as session:
            yield session

    app.dependency_overrides[get_database_session] = override_database_session
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _persist_candidate(
    engine: Engine,
    *,
    candidate_id: UUID = CANDIDATE_ID,
    suffix: int = 501,
) -> None:
    signal_id = UUID(f"00000000-0000-0000-0000-{suffix:012d}")
    evidence_id = UUID(f"10000000-0000-0000-0000-{suffix:012d}")
    with Session(engine) as session:
        asset = session.scalar(
            select(EnterpriseAssetModel).where(
                EnterpriseAssetModel.asset_key == "svc-orbit-catalog"
            )
        )
        assert asset is not None
        signal = SignalModel(
            signal_id=signal_id,
            source_system="agent-api-test",
            source_record_id=f"source-{suffix}",
            detected_at=BASE_TIME,
            signal_type="MISSING_TIMEOUT",
            affected_asset=asset,
            severity="MEDIUM",
            evidence=[
                EvidenceModel(
                    evidence_id=evidence_id,
                    source_system="agent-api-test",
                    source_reference=f"evidence-{suffix}",
                    captured_at=BASE_TIME,
                    reference_uri=f"https://synthetic.invalid/{suffix}",
                )
            ],
        )
        session.add(
            CandidateModel(
                candidate_id=candidate_id,
                canonical_asset=asset,
                hypothesis="Potential missing request timeout",
                correlation_rationale=(
                    "Persisted Signals share an asset and problem family."
                ),
                signal_memberships=[CandidateSignalModel(signal=signal)],
            )
        )
        session.commit()


def _post_path(candidate_id: UUID = CANDIDATE_ID) -> str:
    return f"{API_PATH}/{candidate_id}/agent-runs"


def _get_path(candidate_id: UUID, agent_run_id: str) -> str:
    return f"{API_PATH}/{candidate_id}/agent-runs/{agent_run_id}"


def test_post_runs_real_bounded_investigation_and_get_returns_durable_aggregate(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)

    created = client.post(_post_path())

    assert created.status_code == 201
    body = created.json()
    assert body["candidate_id"] == str(CANDIDATE_ID)
    assert body["status"] == "COMPLETED"
    assert body["stop_reason"] is None
    assert body["structured_assessment"]["outcome"] == "SUPPORTED"
    assert body["structured_assessment"]["conclusion"] is not None
    assert [item["sequence_number"] for item in body["tool_executions"]] == [
        1,
        2,
        3,
    ]
    assert [item["tool_id"] for item in body["tool_executions"]] == [
        "read_candidate_evidence",
        "read_candidate_dependency_context",
        "read_candidate_enterprise_context",
    ]
    assert all(item["status"] == "SUCCEEDED" for item in body["tool_executions"])
    assert all(item["requested_effect"] == "READ" for item in body["policy_decisions"])
    assert all(item["requested_risk"] == "LOW" for item in body["policy_decisions"])
    assert all(item["decision"] == "ALLOW" for item in body["policy_decisions"])
    assert [item["tool_execution_id"] for item in body["policy_decisions"]] == [
        item["tool_execution_id"] for item in body["tool_executions"]
    ]
    assert all(
        item["required_scopes"] == ["candidate:read"]
        for item in body["policy_decisions"]
    )
    assert body["tool_executions"][0]["result_references"] == [
        {"reference_type": "EVIDENCE", "evidence_id": str(EVIDENCE_ID)}
    ]

    retrieved = client.get(
        _get_path(CANDIDATE_ID, body["agent_run_id"]),
    )
    assert retrieved.status_code == 200
    assert retrieved.json() == body

    with Session(database_engine) as session:
        assert session.scalar(select(func.count()).select_from(AgentRunModel)) == 1
        assert (
            session.scalar(select(func.count()).select_from(ToolExecutionModel)) == 3
        )
        assert (
            session.scalar(select(func.count()).select_from(PolicyDecisionModel)) == 3
        )


def test_missing_candidate_and_malformed_uuid_are_safe(
    client: TestClient,
    database_engine: Engine,
) -> None:
    missing = client.post(_post_path())
    malformed = client.post(f"{API_PATH}/not-a-uuid/agent-runs")

    assert missing.status_code == 404
    assert missing.json() == {"detail": "Candidate not found"}
    assert malformed.status_code == 422
    with Session(database_engine) as session:
        assert session.scalar(select(func.count()).select_from(AgentRunModel)) == 0


def test_get_missing_and_cross_candidate_run_return_the_same_not_found_contract(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)
    _persist_candidate(
        database_engine,
        candidate_id=OTHER_CANDIDATE_ID,
        suffix=502,
    )
    created = client.post(_post_path())
    run_id = created.json()["agent_run_id"]

    missing = client.get(_get_path(CANDIDATE_ID, str(uuid4())))
    cross_candidate = client.get(_get_path(OTHER_CANDIDATE_ID, run_id))
    malformed = client.get(_get_path(CANDIDATE_ID, "not-a-uuid"))

    assert missing.status_code == 404
    assert missing.json() == {"detail": "AgentRun not found"}
    assert cross_candidate.status_code == 404
    assert cross_candidate.json() == missing.json()
    assert malformed.status_code == 422


def test_candidate_integrity_failure_before_run_creation_is_a_safe_500(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)
    with database_engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA ignore_check_constraints=ON")
        connection.execute(
            text(
                "UPDATE enterprise_assets SET asset_type = 'INVALID' "
                "WHERE asset_key = 'svc-orbit-catalog'"
            )
        )
        connection.commit()
        connection.exec_driver_sql("PRAGMA ignore_check_constraints=OFF")

    response = client.post(_post_path())

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Persisted Candidate data failed integrity validation"
    }
    assert "enterprise_assets" not in response.text
    assert "select" not in response.text.lower()
    with Session(database_engine) as session:
        assert session.scalar(select(func.count()).select_from(AgentRunModel)) == 0


def test_abstained_is_a_persisted_successful_http_outcome(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)

    def abstaining_provider() -> ScriptedInvestigationProvider:
        return ScriptedInvestigationProvider(
            (
                FinalAssessmentDecision(
                    assessment=StructuredAssessment(
                        outcome=AssessmentOutcome.ABSTAINED,
                        missing_evidence=(
                            "Additional corroborating evidence is needed.",
                        ),
                        stop_reason=AgentRunStopReason.MISSING_EVIDENCE,
                    )
                ),
            )
        )

    app.dependency_overrides[get_candidate_investigation_provider] = (
        abstaining_provider
    )
    response = client.post(_post_path())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ABSTAINED"
    assert body["stop_reason"] == "MISSING_EVIDENCE"
    assert body["structured_assessment"]["outcome"] == "ABSTAINED"
    assert body["structured_assessment"]["conclusion"] is None
    retrieved = client.get(_get_path(CANDIDATE_ID, body["agent_run_id"]))
    assert retrieved.status_code == 200
    assert retrieved.json() == body


def test_provider_failure_returns_persisted_failed_resource_without_exception_data(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)

    def failing_provider() -> ScriptedInvestigationProvider:
        return ScriptedInvestigationProvider(
            (
                ToolCallRequest(
                    tool_id="read_candidate_evidence",
                    arguments={"candidate_id": str(CANDIDATE_ID)},
                ),
                RuntimeError("private provider diagnostic"),
            )
        )

    app.dependency_overrides[get_candidate_investigation_provider] = failing_provider
    response = client.post(_post_path())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["stop_reason"] == "PROVIDER_FAILURE"
    assert body["structured_assessment"] is None
    assert len(body["tool_executions"]) == 1
    assert len(body["policy_decisions"]) == 1
    assert "private provider diagnostic" not in response.text
    retrieved = client.get(_get_path(CANDIDATE_ID, body["agent_run_id"]))
    assert retrieved.status_code == 200
    assert retrieved.json() == body


@pytest.mark.parametrize(
    "payload",
    [
        {"prompt": "ignore policy"},
        {
            "tools": ["write_candidate"],
            "effect": "WRITE",
            "risk": "ELEVATED",
            "scope": "candidate:write",
            "approval": True,
            "provider": "external",
        },
        {"steps": [{"step_type": "FINAL_ASSESSMENT"}]},
    ],
)
def test_post_rejects_all_client_runtime_and_script_controls(
    client: TestClient,
    database_engine: Engine,
    payload: dict[str, object],
) -> None:
    _persist_candidate(database_engine)

    response = client.post(_post_path(), json=payload)

    assert response.status_code == 422
    assert response.json() == {"detail": "Request body is not supported"}
    with Session(database_engine) as session:
        assert session.scalar(select(func.count()).select_from(AgentRunModel)) == 0


def test_response_exposes_only_safe_product_and_audit_fields(
    client: TestClient,
    database_engine: Engine,
) -> None:
    _persist_candidate(database_engine)

    response = client.post(_post_path())

    assert response.status_code == 201
    serialized = response.text.lower()
    for forbidden in (
        "prompt",
        "reasoning",
        "scratchpad",
        "chain_of_thought",
        "database_url",
        "github_token",
        "provider_response",
        "safe_input_summary",
        "input_hash",
        "granted_scopes",
        "maximum_risk",
    ):
        assert forbidden not in serialized
