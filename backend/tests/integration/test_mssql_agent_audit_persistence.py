from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from alembic import command
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
from app.core.config import Settings
from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Evidence, Signal
from app.infrastructure.database.agent_audit_persistence import (
    append_policy_decision,
    append_tool_execution,
    create_agent_run,
    load_agent_run_audit,
    update_agent_run,
)
from app.infrastructure.database.candidate_persistence import persist_candidate
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.signal_persistence import persist_normalized_signal
from app.signal_ingestion import NormalizedSignal


@pytest.mark.integration
def test_mssql_migrates_and_round_trips_agent_audit_aggregate() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")

    backend_root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_root / "alembic.ini")), "head")
    engine = create_database_engine(app_settings)
    try:
        database_inspector = inspect(engine)
        assert {"agent_runs", "tool_executions", "policy_decisions"} <= set(
            database_inspector.get_table_names()
        )
        assert {
            foreign_key["referred_table"]
            for foreign_key in database_inspector.get_foreign_keys("agent_runs")
        } == {"candidates"}
        assert {
            foreign_key["referred_table"]
            for foreign_key in database_inspector.get_foreign_keys(
                "tool_executions"
            )
        } == {"agent_runs"}
        assert {
            foreign_key["referred_table"]
            for foreign_key in database_inspector.get_foreign_keys(
                "policy_decisions"
            )
        } == {"tool_executions"}
        assert "ix_agent_runs_candidate_id" in {
            index["name"] for index in database_inspector.get_indexes("agent_runs")
        }

        with Session(engine) as session:
            transaction = session.begin()
            try:
                seed_enterprise_estate(session)
                timestamp = datetime(2026, 9, 5, 9, 0, tzinfo=UTC)
                evidence = Evidence(
                    evidence_id=uuid4(),
                    source_system="mssql-agent-audit-integration-test",
                    source_reference=f"evidence-{uuid4()}",
                    captured_at=timestamp,
                )
                signal = Signal(
                    signal_id=uuid4(),
                    source_system="mssql-agent-audit-integration-test",
                    source_record_id=f"signal-{uuid4()}",
                    detected_at=timestamp,
                    signal_type="MISSING_TIMEOUT",
                    affected_asset=CanonicalAssetRef(
                        asset_key="repo-borealis-renderer",
                        asset_type=AssetType.REPOSITORY,
                    ),
                    severity="MEDIUM",
                    evidence_ids=frozenset({evidence.evidence_id}),
                )
                persist_normalized_signal(
                    session,
                    NormalizedSignal(signal=signal, evidence=frozenset({evidence})),
                )
                candidate = Candidate(
                    candidate_id=uuid4(),
                    signal_ids=frozenset({signal.signal_id}),
                    evidence_ids=frozenset({evidence.evidence_id}),
                    canonical_asset=signal.affected_asset,
                    hypothesis="Potential missing request timeout",
                    correlation_rationale=(
                        "Signal shares the Candidate asset and problem family."
                    ),
                )
                persist_candidate(session, candidate)

                run_id = uuid4()
                execution_id = uuid4()
                created_at = timestamp + timedelta(seconds=1)
                started_at = created_at + timedelta(seconds=1)
                finished_at = started_at + timedelta(milliseconds=25)
                created_run = AgentRun(
                    agent_run_id=run_id,
                    candidate_id=candidate.candidate_id,
                    status=AgentRunStatus.CREATED,
                    created_at=created_at,
                )
                trace = build_candidate_tool_input_trace(
                    CandidateToolInput(candidate_id=candidate.candidate_id)
                )
                tool_execution = ToolExecution(
                    tool_execution_id=execution_id,
                    agent_run_id=run_id,
                    sequence_number=1,
                    tool_id="read_candidate_evidence",
                    tool_version="1.0",
                    input_hash=trace.input_hash,
                    safe_input_summary=trace.safe_input_summary,
                    status=ToolExecutionStatus.SUCCEEDED,
                    requested_at=started_at,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_ms=25,
                    result_references=(
                        EvidenceReference(evidence_id=evidence.evidence_id),
                    ),
                )
                policy_decision = PolicyDecisionRecord(
                    tool_execution_id=execution_id,
                    decision=PolicyDecision.ALLOW,
                    requested_effect=ToolEffect.READ,
                    requested_risk=ToolRisk.LOW,
                    required_scopes=frozenset({"candidate:read"}),
                    granted_scopes=frozenset({"candidate:read"}),
                    maximum_risk=ToolRisk.LOW,
                    rule_id="allow",
                    reason_code="POLICY_ALLOWED",
                    decided_at=started_at,
                )
                completed_run = AgentRun(
                    agent_run_id=run_id,
                    candidate_id=candidate.candidate_id,
                    status=AgentRunStatus.COMPLETED,
                    created_at=created_at,
                    started_at=started_at,
                    completed_at=finished_at,
                    structured_assessment=StructuredAssessment(
                        outcome=AssessmentOutcome.SUPPORTED,
                        conclusion=GroundedClaim(
                            statement=(
                                "The Candidate has persisted supporting Evidence."
                            ),
                            references=(
                                EvidenceReference(evidence_id=evidence.evidence_id),
                                ToolExecutionReference(
                                    tool_execution_id=execution_id
                                ),
                            ),
                        ),
                        recommendation=(
                            "Present the grounded assessment for human review."
                        ),
                    ),
                )

                create_agent_run(session, created_run)
                append_tool_execution(session, tool_execution)
                append_policy_decision(session, policy_decision)
                update_agent_run(session, completed_run)
                session.flush()
                session.expire_all()

                aggregate = load_agent_run_audit(session, run_id)
                assert aggregate is not None
                assert aggregate.agent_run == completed_run
                assert aggregate.tool_executions == (tool_execution,)
                assert aggregate.policy_decisions == (policy_decision,)
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
