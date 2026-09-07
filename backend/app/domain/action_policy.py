from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ActionPolicyOutcome(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class ActionPolicyReasonCode(StrEnum):
    APPROVAL_MISSING = "APPROVAL_MISSING"
    FINGERPRINT_MISMATCH = "FINGERPRINT_MISMATCH"
    ACTION_TYPE_NOT_ALLOWED = "ACTION_TYPE_NOT_ALLOWED"
    REPOSITORY_NOT_ALLOWLISTED = "REPOSITORY_NOT_ALLOWLISTED"
    EXECUTION_DISABLED = "EXECUTION_DISABLED"
    POLICY_ALLOWED = "POLICY_ALLOWED"


@dataclass(frozen=True)
class ActionPolicyDecision:
    """Append-only L4 execution-policy evaluation. Not an approval or execution."""

    action_policy_decision_id: UUID
    action_proposal_id: UUID
    action_approval_id: UUID | None
    decision: ActionPolicyOutcome
    rule_id: str
    reason_code: ActionPolicyReasonCode
    created_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.decision, ActionPolicyOutcome):
            raise ValueError("ActionPolicyDecision outcome must be supported")
        if not isinstance(self.reason_code, ActionPolicyReasonCode):
            raise ValueError("ActionPolicyDecision reason code must be supported")
        if not self.rule_id.strip():
            raise ValueError("ActionPolicyDecision rule_id must not be blank")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError(
                "ActionPolicyDecision created timestamp must be timezone-aware"
            )
        if (
            self.decision is ActionPolicyOutcome.ALLOW
            and self.action_approval_id is None
        ):
            raise ValueError("ALLOW ActionPolicyDecision requires an ActionApproval")
        if (
            self.decision is ActionPolicyOutcome.ALLOW
            and self.reason_code is not ActionPolicyReasonCode.POLICY_ALLOWED
        ):
            raise ValueError("ALLOW ActionPolicyDecision requires POLICY_ALLOWED")
        if (
            self.decision is ActionPolicyOutcome.DENY
            and self.reason_code is ActionPolicyReasonCode.POLICY_ALLOWED
        ):
            raise ValueError("DENY ActionPolicyDecision cannot use POLICY_ALLOWED")
