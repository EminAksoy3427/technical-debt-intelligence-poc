from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.agent.audit_contracts import (
    AgentRunStatus,
    AgentRunStopReason,
    AssessmentOutcome,
    AssessmentReferenceType,
    StructuredAssessment,
    ToolExecutionStatus,
)
from app.agent.contracts import ToolEffect, ToolRisk
from app.agent.policy import PolicyDecision
from app.infrastructure.database.agent_audit_persistence import (
    AgentRunAuditAggregate,
)


class AgentRunApiResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceReferenceResponse(AgentRunApiResponse):
    reference_type: Literal[AssessmentReferenceType.EVIDENCE]
    evidence_id: UUID


class ToolExecutionReferenceResponse(AgentRunApiResponse):
    reference_type: Literal[AssessmentReferenceType.TOOL_EXECUTION]
    tool_execution_id: UUID


AssessmentReferenceResponse = Annotated[
    EvidenceReferenceResponse | ToolExecutionReferenceResponse,
    Field(discriminator="reference_type"),
]


class GroundedClaimResponse(AgentRunApiResponse):
    statement: str
    references: list[AssessmentReferenceResponse]


class StructuredAssessmentResponse(AgentRunApiResponse):
    outcome: AssessmentOutcome
    conclusion: GroundedClaimResponse | None
    supporting_claims: list[GroundedClaimResponse]
    missing_evidence: list[str]
    uncertainties: list[str]
    recommendation: str | None
    stop_reason: AgentRunStopReason | None


class ToolExecutionResponse(AgentRunApiResponse):
    tool_execution_id: UUID
    sequence_number: int
    tool_id: str
    tool_version: str
    status: ToolExecutionStatus
    duration_ms: int
    error_code: str | None
    error_message: str | None
    result_references: list[EvidenceReferenceResponse]


class PolicyDecisionResponse(AgentRunApiResponse):
    tool_execution_id: UUID
    decision: PolicyDecision
    requested_effect: ToolEffect
    requested_risk: ToolRisk
    required_scopes: list[str]
    rule_id: str
    reason_code: str
    decided_at: datetime


class AgentRunResponse(AgentRunApiResponse):
    agent_run_id: UUID
    candidate_id: UUID
    status: AgentRunStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    stop_reason: AgentRunStopReason | None
    structured_assessment: StructuredAssessmentResponse | None
    tool_executions: list[ToolExecutionResponse]
    policy_decisions: list[PolicyDecisionResponse]


def agent_run_response(aggregate: AgentRunAuditAggregate) -> AgentRunResponse:
    agent_run = aggregate.agent_run
    return AgentRunResponse(
        agent_run_id=agent_run.agent_run_id,
        candidate_id=agent_run.candidate_id,
        status=agent_run.status,
        created_at=agent_run.created_at,
        started_at=agent_run.started_at,
        completed_at=agent_run.completed_at,
        stop_reason=agent_run.stop_reason,
        structured_assessment=_structured_assessment_response(
            agent_run.structured_assessment
        ),
        tool_executions=[
            ToolExecutionResponse.model_validate(
                {
                    "tool_execution_id": execution.tool_execution_id,
                    "sequence_number": execution.sequence_number,
                    "tool_id": execution.tool_id,
                    "tool_version": execution.tool_version,
                    "status": execution.status.value,
                    "duration_ms": execution.duration_ms,
                    "error_code": execution.error_code,
                    "error_message": execution.error_message,
                    "result_references": [
                        reference.model_dump(mode="json")
                        for reference in execution.result_references
                    ],
                }
            )
            for execution in aggregate.tool_executions
        ],
        policy_decisions=[
            PolicyDecisionResponse(
                tool_execution_id=decision.tool_execution_id,
                decision=decision.decision,
                requested_effect=decision.requested_effect,
                requested_risk=decision.requested_risk,
                required_scopes=sorted(decision.required_scopes),
                rule_id=decision.rule_id,
                reason_code=decision.reason_code,
                decided_at=decision.decided_at,
            )
            for decision in aggregate.policy_decisions
        ],
    )


def _structured_assessment_response(
    assessment: StructuredAssessment | None,
) -> StructuredAssessmentResponse | None:
    if assessment is None:
        return None
    return StructuredAssessmentResponse.model_validate(
        assessment.model_dump(mode="json")
    )
