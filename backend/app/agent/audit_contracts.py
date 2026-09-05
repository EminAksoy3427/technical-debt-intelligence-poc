import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.agent.contracts import CandidateToolInput, ToolEffect, ToolRisk
from app.agent.policy import PolicyDecision

NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
SafeErrorCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
SafeErrorMessage = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1000),
]
Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class AuditContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AssessmentOutcome(StrEnum):
    SUPPORTED = "SUPPORTED"
    ABSTAINED = "ABSTAINED"


class AgentRunStatus(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ABSTAINED = "ABSTAINED"
    FAILED = "FAILED"


class AgentRunStopReason(StrEnum):
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    POLICY_DENIED = "POLICY_DENIED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_UNAVAILABLE = "TOOL_UNAVAILABLE"
    INVALID_TOOL_ARGUMENTS = "INVALID_TOOL_ARGUMENTS"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    INTERNAL_FAILURE = "INTERNAL_FAILURE"


class AssessmentReferenceType(StrEnum):
    EVIDENCE = "EVIDENCE"
    TOOL_EXECUTION = "TOOL_EXECUTION"


class EvidenceReference(AuditContract):
    reference_type: Literal[AssessmentReferenceType.EVIDENCE] = (
        AssessmentReferenceType.EVIDENCE
    )
    evidence_id: UUID


class ToolExecutionReference(AuditContract):
    reference_type: Literal[AssessmentReferenceType.TOOL_EXECUTION] = (
        AssessmentReferenceType.TOOL_EXECUTION
    )
    tool_execution_id: UUID


AssessmentReference = Annotated[
    EvidenceReference | ToolExecutionReference,
    Field(discriminator="reference_type"),
]


class GroundedClaim(AuditContract):
    statement: NonBlankText
    references: tuple[AssessmentReference, ...] = Field(min_length=1)


class StructuredAssessment(AuditContract):
    outcome: AssessmentOutcome
    conclusion: GroundedClaim | None = None
    supporting_claims: tuple[GroundedClaim, ...] = ()
    missing_evidence: tuple[NonBlankText, ...] = ()
    uncertainties: tuple[NonBlankText, ...] = ()
    recommendation: NonBlankText | None = None
    stop_reason: AgentRunStopReason | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> "StructuredAssessment":
        if self.outcome is AssessmentOutcome.SUPPORTED:
            if self.conclusion is None:
                raise ValueError("SUPPORTED assessment requires a grounded conclusion")
            return self

        if self.conclusion is not None:
            raise ValueError("ABSTAINED assessment must not contain a conclusion")
        if not (self.missing_evidence or self.uncertainties or self.stop_reason):
            raise ValueError("ABSTAINED assessment requires a meaningful reason")
        return self


class AgentRun(AuditContract):
    agent_run_id: UUID
    candidate_id: UUID
    status: AgentRunStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    structured_assessment: StructuredAssessment | None = None
    stop_reason: AgentRunStopReason | None = None

    @field_validator("created_at", "started_at", "completed_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("AgentRun timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_state(self) -> "AgentRun":
        if self.started_at is not None and self.started_at < self.created_at:
            raise ValueError("AgentRun start cannot precede creation")
        if self.completed_at is not None:
            lower_bound = self.started_at or self.created_at
            if self.completed_at < lower_bound:
                raise ValueError("AgentRun completion cannot precede its start")

        if self.status is AgentRunStatus.CREATED:
            if any(
                value is not None
                for value in (
                    self.started_at,
                    self.completed_at,
                    self.structured_assessment,
                    self.stop_reason,
                )
            ):
                raise ValueError("CREATED AgentRun cannot contain execution results")
        elif self.status is AgentRunStatus.RUNNING:
            if self.started_at is None or any(
                value is not None
                for value in (
                    self.completed_at,
                    self.structured_assessment,
                    self.stop_reason,
                )
            ):
                raise ValueError("RUNNING AgentRun requires only a start timestamp")
        elif self.status is AgentRunStatus.COMPLETED:
            if self.started_at is None or self.completed_at is None:
                raise ValueError("COMPLETED AgentRun requires start and completion")
            if (
                self.structured_assessment is None
                or self.structured_assessment.outcome is not AssessmentOutcome.SUPPORTED
            ):
                raise ValueError(
                    "COMPLETED AgentRun requires a supported Structured Assessment"
                )
            if self.stop_reason is not None:
                raise ValueError("COMPLETED AgentRun must not contain a stop reason")
        elif self.status is AgentRunStatus.ABSTAINED:
            if self.started_at is None or self.completed_at is None:
                raise ValueError("ABSTAINED AgentRun requires start and completion")
            if self.stop_reason is None:
                raise ValueError("ABSTAINED AgentRun requires a stop reason")
            if (
                self.structured_assessment is not None
                and self.structured_assessment.outcome
                is not AssessmentOutcome.ABSTAINED
            ):
                raise ValueError(
                    "ABSTAINED AgentRun cannot contain a supported assessment"
                )
        else:
            if self.completed_at is None or self.stop_reason is None:
                raise ValueError("FAILED AgentRun requires completion and stop reason")
            if self.structured_assessment is not None:
                raise ValueError("FAILED AgentRun must not contain an assessment")
        return self


class ToolExecutionStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    DENIED = "DENIED"
    INVALID_ARGUMENTS = "INVALID_ARGUMENTS"
    TIMED_OUT = "TIMED_OUT"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"


class CandidateToolInputSummary(AuditContract):
    candidate_id: UUID


class CandidateToolInputTrace(AuditContract):
    input_hash: Sha256Hex
    safe_input_summary: CandidateToolInputSummary


def build_candidate_tool_input_trace(
    tool_input: CandidateToolInput,
) -> CandidateToolInputTrace:
    """Create a deterministic identity from the allowlisted Candidate input."""
    validated_input = CandidateToolInput.model_validate(tool_input)
    summary = CandidateToolInputSummary(candidate_id=validated_input.candidate_id)
    canonical_input = json.dumps(
        summary.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return CandidateToolInputTrace(
        input_hash=hashlib.sha256(canonical_input).hexdigest(),
        safe_input_summary=summary,
    )


class ToolExecution(AuditContract):
    tool_execution_id: UUID
    agent_run_id: UUID
    sequence_number: Annotated[int, Field(ge=1)]
    tool_id: NonBlankText
    tool_version: NonBlankText
    input_hash: Sha256Hex
    safe_input_summary: CandidateToolInputSummary
    status: ToolExecutionStatus
    requested_at: datetime
    started_at: datetime | None = None
    finished_at: datetime
    duration_ms: Annotated[int, Field(ge=0)]
    error_code: SafeErrorCode | None = None
    error_message: SafeErrorMessage | None = None
    result_references: tuple[EvidenceReference, ...] = ()

    @field_validator("requested_at", "started_at", "finished_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("ToolExecution timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_result(self) -> "ToolExecution":
        if self.started_at is not None and self.started_at < self.requested_at:
            raise ValueError("ToolExecution start cannot precede its request")
        if self.finished_at < (self.started_at or self.requested_at):
            raise ValueError("ToolExecution finish cannot precede its start")

        requires_execution_start = {
            ToolExecutionStatus.SUCCEEDED,
            ToolExecutionStatus.TIMED_OUT,
            ToolExecutionStatus.FAILED,
        }
        if self.status in requires_execution_start and self.started_at is None:
            raise ValueError("Executed ToolExecution status requires a start timestamp")
        if self.status is ToolExecutionStatus.SUCCEEDED:
            if self.error_code is not None or self.error_message is not None:
                raise ValueError("SUCCEEDED ToolExecution must not contain an error")
        elif self.error_code is None:
            raise ValueError("Unsuccessful ToolExecution requires a safe error code")
        return self


class PolicyDecisionRecord(AuditContract):
    tool_execution_id: UUID
    decision: PolicyDecision
    requested_effect: ToolEffect
    requested_risk: ToolRisk
    required_scopes: frozenset[NonBlankText]
    granted_scopes: frozenset[NonBlankText]
    maximum_risk: ToolRisk
    rule_id: NonBlankText
    reason_code: NonBlankText
    decided_at: datetime

    @field_validator("decided_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("PolicyDecision timestamp must be timezone-aware")
        return value
