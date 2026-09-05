from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.agent.audit_contracts import (
    AgentRun,
    AgentRunStatus,
    CandidateToolInputSummary,
    EvidenceReference,
    PolicyDecisionRecord,
    StructuredAssessment,
    ToolExecution,
)
from app.infrastructure.database.agent_audit_models import (
    AgentRunModel,
    PolicyDecisionModel,
    ToolExecutionModel,
)
from app.infrastructure.database.candidate_models import CandidateModel


@dataclass(frozen=True)
class AgentRunAuditAggregate:
    agent_run: AgentRun
    tool_executions: tuple[ToolExecution, ...]
    policy_decisions: tuple[PolicyDecisionRecord, ...]


def create_agent_run(session: Session, agent_run: AgentRun) -> None:
    """Create one AgentRun in the caller-owned transaction."""
    if agent_run.status is not AgentRunStatus.CREATED:
        raise ValueError("New AgentRun must have CREATED status")
    if session.get(CandidateModel, agent_run.candidate_id) is None:
        raise ValueError("AgentRun Candidate does not exist")

    session.add(_agent_run_model(agent_run))
    session.flush()


def get_agent_run(session: Session, agent_run_id: UUID) -> AgentRun | None:
    persisted_run = session.get(AgentRunModel, agent_run_id)
    if persisted_run is None:
        return None
    return _agent_run_contract(persisted_run)


def update_agent_run(session: Session, agent_run: AgentRun) -> None:
    """Replace mutable AgentRun state without owning the transaction."""
    persisted_run = session.get(AgentRunModel, agent_run.agent_run_id)
    if persisted_run is None:
        raise ValueError("AgentRun does not exist")
    if persisted_run.candidate_id != agent_run.candidate_id:
        raise ValueError("AgentRun Candidate identity cannot change")
    if _as_timezone_aware(persisted_run.created_at) != agent_run.created_at:
        raise ValueError("AgentRun creation timestamp cannot change")

    persisted_run.status = agent_run.status.value
    persisted_run.started_at = agent_run.started_at
    persisted_run.completed_at = agent_run.completed_at
    persisted_run.structured_assessment = _assessment_json(
        agent_run.structured_assessment
    )
    persisted_run.stop_reason = (
        agent_run.stop_reason.value if agent_run.stop_reason is not None else None
    )
    session.flush()


def append_tool_execution(
    session: Session,
    tool_execution: ToolExecution,
) -> None:
    """Append one terminal ToolExecution audit record."""
    if session.get(AgentRunModel, tool_execution.agent_run_id) is None:
        raise ValueError("ToolExecution AgentRun does not exist")

    session.add(
        ToolExecutionModel(
            tool_execution_id=tool_execution.tool_execution_id,
            agent_run_id=tool_execution.agent_run_id,
            sequence_number=tool_execution.sequence_number,
            tool_id=tool_execution.tool_id,
            tool_version=tool_execution.tool_version,
            input_hash=tool_execution.input_hash,
            safe_input_summary=tool_execution.safe_input_summary.model_dump(
                mode="json"
            ),
            status=tool_execution.status.value,
            requested_at=tool_execution.requested_at,
            started_at=tool_execution.started_at,
            finished_at=tool_execution.finished_at,
            duration_ms=tool_execution.duration_ms,
            error_code=tool_execution.error_code,
            error_message=tool_execution.error_message,
            result_references=[
                reference.model_dump(mode="json")
                for reference in tool_execution.result_references
            ],
        )
    )
    session.flush()


def append_policy_decision(
    session: Session,
    policy_decision: PolicyDecisionRecord,
) -> None:
    """Append the single PolicyDecision for a ToolExecution."""
    if session.get(ToolExecutionModel, policy_decision.tool_execution_id) is None:
        raise ValueError("PolicyDecision ToolExecution does not exist")

    session.add(
        PolicyDecisionModel(
            tool_execution_id=policy_decision.tool_execution_id,
            decision=policy_decision.decision.value,
            requested_effect=policy_decision.requested_effect.value,
            requested_risk=policy_decision.requested_risk.value,
            required_scopes=sorted(policy_decision.required_scopes),
            granted_scopes=sorted(policy_decision.granted_scopes),
            maximum_risk=policy_decision.maximum_risk.value,
            rule_id=policy_decision.rule_id,
            reason_code=policy_decision.reason_code,
            decided_at=policy_decision.decided_at,
        )
    )
    session.flush()


def load_agent_run_audit(
    session: Session,
    agent_run_id: UUID,
) -> AgentRunAuditAggregate | None:
    return _load_agent_run_audit(session, agent_run_id=agent_run_id)


def load_candidate_agent_run_audit(
    session: Session,
    *,
    candidate_id: UUID,
    agent_run_id: UUID,
) -> AgentRunAuditAggregate | None:
    """Load one aggregate only when it belongs to the supplied Candidate."""
    return _load_agent_run_audit(
        session,
        agent_run_id=agent_run_id,
        candidate_id=candidate_id,
    )


def _load_agent_run_audit(
    session: Session,
    *,
    agent_run_id: UUID,
    candidate_id: UUID | None = None,
) -> AgentRunAuditAggregate | None:
    statement = (
        select(AgentRunModel)
        .options(
            selectinload(AgentRunModel.tool_executions).selectinload(
                ToolExecutionModel.policy_decision
            )
        )
        .where(AgentRunModel.agent_run_id == agent_run_id)
    )
    if candidate_id is not None:
        statement = statement.where(AgentRunModel.candidate_id == candidate_id)
    persisted_run = session.scalar(statement)
    if persisted_run is None:
        return None

    tool_executions = tuple(
        _tool_execution_contract(execution)
        for execution in persisted_run.tool_executions
    )
    policy_decisions = tuple(
        _policy_decision_contract(execution.policy_decision)
        for execution in persisted_run.tool_executions
        if execution.policy_decision is not None
    )
    return AgentRunAuditAggregate(
        agent_run=_agent_run_contract(persisted_run),
        tool_executions=tool_executions,
        policy_decisions=policy_decisions,
    )


def _agent_run_model(agent_run: AgentRun) -> AgentRunModel:
    return AgentRunModel(
        agent_run_id=agent_run.agent_run_id,
        candidate_id=agent_run.candidate_id,
        status=agent_run.status.value,
        created_at=agent_run.created_at,
        started_at=agent_run.started_at,
        completed_at=agent_run.completed_at,
        structured_assessment=_assessment_json(agent_run.structured_assessment),
        stop_reason=(
            agent_run.stop_reason.value if agent_run.stop_reason is not None else None
        ),
    )


def _agent_run_contract(persisted_run: AgentRunModel) -> AgentRun:
    return AgentRun.model_validate(
        {
            "agent_run_id": persisted_run.agent_run_id,
            "candidate_id": persisted_run.candidate_id,
            "status": persisted_run.status,
            "created_at": _as_timezone_aware(persisted_run.created_at),
            "started_at": _optional_timezone_aware(persisted_run.started_at),
            "completed_at": _optional_timezone_aware(persisted_run.completed_at),
            "structured_assessment": persisted_run.structured_assessment,
            "stop_reason": persisted_run.stop_reason,
        }
    )


def _tool_execution_contract(
    persisted_execution: ToolExecutionModel,
) -> ToolExecution:
    return ToolExecution.model_validate(
        {
            "tool_execution_id": persisted_execution.tool_execution_id,
            "agent_run_id": persisted_execution.agent_run_id,
            "sequence_number": persisted_execution.sequence_number,
            "tool_id": persisted_execution.tool_id,
            "tool_version": persisted_execution.tool_version,
            "input_hash": persisted_execution.input_hash,
            "safe_input_summary": CandidateToolInputSummary.model_validate(
                persisted_execution.safe_input_summary
            ),
            "status": persisted_execution.status,
            "requested_at": _as_timezone_aware(persisted_execution.requested_at),
            "started_at": _optional_timezone_aware(persisted_execution.started_at),
            "finished_at": _as_timezone_aware(persisted_execution.finished_at),
            "duration_ms": persisted_execution.duration_ms,
            "error_code": persisted_execution.error_code,
            "error_message": persisted_execution.error_message,
            "result_references": [
                EvidenceReference.model_validate(reference)
                for reference in persisted_execution.result_references
            ],
        }
    )


def _policy_decision_contract(
    persisted_decision: PolicyDecisionModel,
) -> PolicyDecisionRecord:
    return PolicyDecisionRecord.model_validate(
        {
            "tool_execution_id": persisted_decision.tool_execution_id,
            "decision": persisted_decision.decision,
            "requested_effect": persisted_decision.requested_effect,
            "requested_risk": persisted_decision.requested_risk,
            "required_scopes": persisted_decision.required_scopes,
            "granted_scopes": persisted_decision.granted_scopes,
            "maximum_risk": persisted_decision.maximum_risk,
            "rule_id": persisted_decision.rule_id,
            "reason_code": persisted_decision.reason_code,
            "decided_at": _as_timezone_aware(persisted_decision.decided_at),
        }
    )


def _assessment_json(
    assessment: StructuredAssessment | None,
) -> dict[str, object] | None:
    if assessment is None:
        return None
    return assessment.model_dump(mode="json")


def _optional_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return _as_timezone_aware(value)


def _as_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value
