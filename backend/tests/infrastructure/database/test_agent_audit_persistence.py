from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agent.audit_contracts import (
    AgentRun,
    AgentRunStatus,
    AssessmentOutcome,
    EvidenceReference,
    GroundedClaim,
    PolicyDecisionRecord,
    StructuredAssessment,
    ToolExecution,
    ToolExecutionReference,
    ToolExecutionStatus,
    build_candidate_tool_input_trace,
)
from app.agent.contracts import CandidateToolInput, ToolEffect, ToolRisk
from app.agent.policy import PolicyDecision
from app.infrastructure.database.agent_audit_models import (
    AgentRunModel,
    PolicyDecisionModel,
    ToolExecutionModel,
)
from app.infrastructure.database.agent_audit_persistence import (
    append_policy_decision,
    append_tool_execution,
    create_agent_run,
    get_agent_run,
    load_agent_run_audit,
    load_candidate_agent_run_audit,
    update_agent_run,
)
from app.infrastructure.database.candidate_models import (
    CandidateModel,
    CandidateSignalModel,
)
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel

CREATED_AT = datetime(2026, 9, 5, 9, 0, tzinfo=UTC)
STARTED_AT = CREATED_AT + timedelta(seconds=1)
FINISHED_AT = STARTED_AT + timedelta(milliseconds=25)
CANDIDATE_ID = UUID("00000000-0000-0000-0000-000000000701")
EVIDENCE_ID = UUID("00000000-0000-0000-0000-000000000601")
RUN_ID = UUID("00000000-0000-0000-0000-000000000901")
EXECUTION_ID = UUID("00000000-0000-0000-0000-000000000801")


@pytest.fixture
def database_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(
        dbapi_connection: object,
        _connection_record: object,
    ) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]

    backend_root = Path(__file__).resolve().parents[3]
    scripts = ScriptDirectory.from_config(Config(str(backend_root / "alembic.ini")))
    revisions = list(scripts.walk_revisions(base="base", head="heads"))
    with engine.begin() as connection:
        operations = Operations(MigrationContext.configure(connection))
        for revision in reversed(revisions):
            monkeypatch.setattr(revision.module, "op", operations, raising=False)
            revision.module.upgrade()

    with Session(engine) as session:
        asset = EnterpriseAssetModel(
            asset_key="repo-borealis-renderer",
            asset_type="REPOSITORY",
            name="Borealis Renderer Repository",
            criticality="MEDIUM",
            lifecycle_status="ACTIVE",
        )
        signal_id = UUID("00000000-0000-0000-0000-000000000501")
        signal = SignalModel(
            signal_id=signal_id,
            source_system="agent-audit-persistence-test",
            source_record_id="source-501",
            detected_at=CREATED_AT,
            signal_type="MISSING_TIMEOUT",
            affected_asset=asset,
            severity="MEDIUM",
            evidence=[
                EvidenceModel(
                    evidence_id=EVIDENCE_ID,
                    source_system="agent-audit-persistence-test",
                    source_reference="source-501",
                    captured_at=CREATED_AT,
                )
            ],
        )
        session.add(
            CandidateModel(
                candidate_id=CANDIDATE_ID,
                canonical_asset=asset,
                hypothesis="Potential missing request timeout",
                correlation_rationale=(
                    "Persisted Signals share an asset and problem family."
                ),
                signal_memberships=[CandidateSignalModel(signal=signal)],
            )
        )
        session.commit()

    yield engine
    engine.dispose()


def _created_run() -> AgentRun:
    return AgentRun(
        agent_run_id=RUN_ID,
        candidate_id=CANDIDATE_ID,
        status=AgentRunStatus.CREATED,
        created_at=CREATED_AT,
    )


def _tool_execution(
    *,
    tool_execution_id: UUID = EXECUTION_ID,
    sequence_number: int = 1,
) -> ToolExecution:
    trace = build_candidate_tool_input_trace(
        CandidateToolInput(candidate_id=CANDIDATE_ID)
    )
    return ToolExecution(
        tool_execution_id=tool_execution_id,
        agent_run_id=RUN_ID,
        sequence_number=sequence_number,
        tool_id="read_candidate_evidence",
        tool_version="1.0",
        input_hash=trace.input_hash,
        safe_input_summary=trace.safe_input_summary,
        status=ToolExecutionStatus.SUCCEEDED,
        requested_at=STARTED_AT,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        duration_ms=25,
        result_references=(EvidenceReference(evidence_id=EVIDENCE_ID),),
    )


def _policy_decision(
    *,
    tool_execution_id: UUID = EXECUTION_ID,
) -> PolicyDecisionRecord:
    return PolicyDecisionRecord(
        tool_execution_id=tool_execution_id,
        decision=PolicyDecision.ALLOW,
        requested_effect=ToolEffect.READ,
        requested_risk=ToolRisk.LOW,
        required_scopes=frozenset({"candidate:read"}),
        granted_scopes=frozenset({"candidate:read"}),
        maximum_risk=ToolRisk.LOW,
        rule_id="allow",
        reason_code="POLICY_ALLOWED",
        decided_at=STARTED_AT,
    )


def _completed_run() -> AgentRun:
    assessment = StructuredAssessment(
        outcome=AssessmentOutcome.SUPPORTED,
        conclusion=GroundedClaim(
            statement="The Candidate has persisted supporting Evidence.",
            references=(
                EvidenceReference(evidence_id=EVIDENCE_ID),
                ToolExecutionReference(tool_execution_id=EXECUTION_ID),
            ),
        ),
        recommendation="Present the grounded assessment for human review.",
    )
    return AgentRun(
        agent_run_id=RUN_ID,
        candidate_id=CANDIDATE_ID,
        status=AgentRunStatus.COMPLETED,
        created_at=CREATED_AT,
        started_at=STARTED_AT,
        completed_at=FINISHED_AT,
        structured_assessment=assessment,
    )


def test_create_update_and_load_complete_audit_aggregate(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        create_agent_run(session, _created_run())
        append_tool_execution(session, _tool_execution())
        append_policy_decision(session, _policy_decision())
        update_agent_run(session, _completed_run())
        session.commit()

    with Session(database_engine) as session:
        aggregate = load_agent_run_audit(session, RUN_ID)
        assert aggregate is not None
        assert aggregate.agent_run == _completed_run()
        assert aggregate.tool_executions == (_tool_execution(),)
        assert aggregate.policy_decisions == (_policy_decision(),)
        assert get_agent_run(session, RUN_ID) == _completed_run()

        persisted_execution = session.get(ToolExecutionModel, EXECUTION_ID)
        assert persisted_execution is not None
        assert persisted_execution.safe_input_summary == {
            "candidate_id": str(CANDIDATE_ID)
        }
        assert persisted_execution.result_references == [
            {
                "reference_type": "EVIDENCE",
                "evidence_id": str(EVIDENCE_ID),
            }
        ]


def test_repository_functions_leave_transaction_ownership_to_caller(
    database_engine: Engine,
) -> None:
    committed = False

    def mark_commit(_session: Session) -> None:
        nonlocal committed
        committed = True

    with Session(database_engine) as session:
        event.listen(session, "before_commit", mark_commit)
        create_agent_run(session, _created_run())
        append_tool_execution(session, _tool_execution())
        append_policy_decision(session, _policy_decision())
        assert committed is False


def test_agent_run_requires_a_persisted_candidate(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        unknown_candidate_run = _created_run().model_copy(
            update={"candidate_id": uuid4()}
        )
        with pytest.raises(ValueError, match="Candidate does not exist"):
            create_agent_run(session, unknown_candidate_run)


def test_sequence_number_is_unique_within_one_run(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        create_agent_run(session, _created_run())
        append_tool_execution(session, _tool_execution())
        duplicate_sequence = _tool_execution(tool_execution_id=uuid4())
        with pytest.raises(IntegrityError):
            append_tool_execution(session, duplicate_sequence)


def test_policy_decision_is_unique_per_tool_execution(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        create_agent_run(session, _created_run())
        append_tool_execution(session, _tool_execution())
        append_policy_decision(session, _policy_decision())
        with pytest.raises(IntegrityError):
            append_policy_decision(session, _policy_decision())


def test_database_rejects_negative_duration(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        create_agent_run(session, _created_run())
        valid = _tool_execution()
        session.add(
            ToolExecutionModel(
                tool_execution_id=valid.tool_execution_id,
                agent_run_id=valid.agent_run_id,
                sequence_number=valid.sequence_number,
                tool_id=valid.tool_id,
                tool_version=valid.tool_version,
                input_hash=valid.input_hash,
                safe_input_summary=valid.safe_input_summary.model_dump(mode="json"),
                status=valid.status.value,
                requested_at=valid.requested_at,
                started_at=valid.started_at,
                finished_at=valid.finished_at,
                duration_ms=-1,
                result_references=[],
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_relationships_link_candidate_run_execution_and_policy(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        create_agent_run(session, _created_run())
        append_tool_execution(session, _tool_execution())
        append_policy_decision(session, _policy_decision())

        candidate = session.get(CandidateModel, CANDIDATE_ID)
        run = session.get(AgentRunModel, RUN_ID)
        decision = session.get(PolicyDecisionModel, EXECUTION_ID)
        assert candidate is not None
        assert run is not None
        assert decision is not None
        assert list(candidate.agent_runs) == [run]
        persisted_execution = session.get(ToolExecutionModel, EXECUTION_ID)
        assert list(run.tool_executions) == [persisted_execution]
        assert decision.tool_execution is run.tool_executions[0]


def test_load_missing_run_returns_none(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        assert load_agent_run_audit(session, uuid4()) is None
        assert get_agent_run(session, uuid4()) is None


def test_candidate_scoped_load_does_not_return_another_candidates_run(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        create_agent_run(session, _created_run())
        session.commit()

    with Session(database_engine) as session:
        matching = load_candidate_agent_run_audit(
            session,
            candidate_id=CANDIDATE_ID,
            agent_run_id=RUN_ID,
        )
        cross_candidate = load_candidate_agent_run_audit(
            session,
            candidate_id=uuid4(),
            agent_run_id=RUN_ID,
        )

    assert matching is not None
    assert cross_candidate is None


def test_audit_tables_contain_only_the_expected_rows(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        create_agent_run(session, _created_run())
        assert session.scalars(select(AgentRunModel)).all() != []
        assert session.scalars(select(ToolExecutionModel)).all() == []
        assert session.scalars(select(PolicyDecisionModel)).all() == []
