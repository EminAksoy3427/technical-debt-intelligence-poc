from typing import Annotated, Literal, Protocol
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
)

from app.agent.audit_contracts import AssessmentReference, ToolExecutionStatus
from app.agent.contracts import ToolEffect, ToolRisk

NonBlankIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class RuntimeContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RuntimeToolDescriptor(RuntimeContract):
    tool_id: NonBlankIdentifier
    version: NonBlankIdentifier
    description: NonBlankIdentifier
    effect: ToolEffect
    risk: ToolRisk
    required_scopes: tuple[NonBlankIdentifier, ...]


class ToolResultObservation(RuntimeContract):
    tool_execution_id: UUID
    sequence_number: Annotated[int, Field(ge=1)]
    tool_id: NonBlankIdentifier
    tool_version: NonBlankIdentifier
    status: ToolExecutionStatus
    result: dict[str, JsonValue] | None = None
    references: tuple[AssessmentReference, ...] = ()
    error_code: NonBlankIdentifier | None = None


class InvestigationRuntimeContext(RuntimeContract):
    candidate_id: UUID
    available_tools: tuple[RuntimeToolDescriptor, ...]
    tool_results: tuple[ToolResultObservation, ...]
    remaining_iterations: Annotated[int, Field(ge=1)]
    remaining_tool_calls: Annotated[int, Field(ge=0)]


class ToolCallRequest(RuntimeContract):
    step_type: Literal["TOOL_CALL"] = "TOOL_CALL"
    tool_id: NonBlankIdentifier
    arguments: dict[str, JsonValue]


class FinalAssessmentDecision(RuntimeContract):
    step_type: Literal["FINAL_ASSESSMENT"] = "FINAL_ASSESSMENT"
    assessment: object


ProviderStep = Annotated[
    ToolCallRequest | FinalAssessmentDecision,
    Field(discriminator="step_type"),
]


class InvestigationProvider(Protocol):
    """Decision port for one bounded, source-independent investigation step."""

    def next_step(self, context: InvestigationRuntimeContext) -> ProviderStep: ...


class AgentRuntimeLimits(RuntimeContract):
    max_iterations: Annotated[int, Field(gt=0)] = 6
    max_tool_calls: Annotated[int, Field(gt=0)] = 3
    run_timeout_seconds: Annotated[int, Field(gt=0)] = 60
    tool_timeout_seconds: Annotated[int, Field(gt=0)] = 5
