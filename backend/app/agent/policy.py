from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID

from pydantic import BaseModel

from app.agent.contracts import (
    CandidateToolInput,
    ToolEffect,
    ToolRegistration,
    ToolRisk,
)

_RISK_ORDER = MappingProxyType(
    {
        ToolRisk.LOW: 0,
        ToolRisk.ELEVATED: 1,
    }
)


class PolicyDecision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass(frozen=True)
class ToolAuthorizationContext:
    """Trusted server-owned limits for one temporary investigation."""

    investigation_id: UUID
    candidate_id: UUID
    allowed_effects: frozenset[ToolEffect]
    maximum_risk: ToolRisk
    granted_scopes: frozenset[str]

    def __post_init__(self) -> None:
        allowed_effects = frozenset(self.allowed_effects)
        granted_scopes = frozenset(self.granted_scopes)
        if any(not isinstance(effect, ToolEffect) for effect in allowed_effects):
            raise ValueError("Authorization effects must be supported")
        if not isinstance(self.maximum_risk, ToolRisk):
            raise ValueError("Authorization maximum risk must be supported")
        if any(not scope.strip() for scope in granted_scopes):
            raise ValueError("Authorization scopes must not contain blanks")
        object.__setattr__(self, "allowed_effects", allowed_effects)
        object.__setattr__(self, "granted_scopes", granted_scopes)


@dataclass(frozen=True)
class ToolPolicyResult:
    decision: PolicyDecision
    rule_id: str
    reason_code: str


@dataclass(frozen=True)
class ToolExecutionResult[ResultModelT: BaseModel]:
    policy: ToolPolicyResult
    result: ResultModelT | None


def evaluate_candidate_tool_policy(
    registration: ToolRegistration[BaseModel, BaseModel],
    candidate_id: UUID,
    authorization: ToolAuthorizationContext,
) -> ToolPolicyResult:
    """Evaluate trusted authorization limits in a fixed, deterministic order."""
    descriptor = registration.descriptor
    if candidate_id != authorization.candidate_id:
        return ToolPolicyResult(
            decision=PolicyDecision.DENY,
            rule_id="candidate_scope",
            reason_code="CANDIDATE_MISMATCH",
        )
    if descriptor.effect not in authorization.allowed_effects:
        return ToolPolicyResult(
            decision=PolicyDecision.DENY,
            rule_id="tool_effect",
            reason_code="EFFECT_NOT_ALLOWED",
        )
    if not descriptor.required_scopes.issubset(authorization.granted_scopes):
        return ToolPolicyResult(
            decision=PolicyDecision.DENY,
            rule_id="required_scopes",
            reason_code="REQUIRED_SCOPE_MISSING",
        )
    if _RISK_ORDER[descriptor.risk] > _RISK_ORDER[authorization.maximum_risk]:
        return ToolPolicyResult(
            decision=PolicyDecision.DENY,
            rule_id="tool_risk",
            reason_code="RISK_EXCEEDS_MAXIMUM",
        )
    return ToolPolicyResult(
        decision=PolicyDecision.ALLOW,
        rule_id="allow",
        reason_code="POLICY_ALLOWED",
    )


def execute_candidate_tool[
    InputModelT: CandidateToolInput,
    ResultModelT: BaseModel,
](
    registration: ToolRegistration[InputModelT, ResultModelT],
    tool_input: object,
    authorization: ToolAuthorizationContext,
) -> ToolExecutionResult[ResultModelT]:
    """Validate, authorize, and only then execute one Candidate tool."""
    validated_input = registration.input_model.model_validate(tool_input)
    policy = evaluate_candidate_tool_policy(
        registration,
        validated_input.candidate_id,
        authorization,
    )
    if policy.decision is PolicyDecision.DENY:
        return ToolExecutionResult(policy=policy, result=None)

    executor_result = registration.executor(validated_input)
    validated_result = registration.result_model.model_validate(executor_result)
    return ToolExecutionResult(policy=policy, result=validated_result)
