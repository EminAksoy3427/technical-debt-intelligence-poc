from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.domain.action_policy import (
    ActionPolicyDecision,
    ActionPolicyOutcome,
    ActionPolicyReasonCode,
)

CREATED_AT = datetime(2026, 9, 7, 17, 30, tzinfo=UTC)
DECISION_ID = UUID("00000000-0000-0000-0000-000000000701")
PROPOSAL_ID = UUID("00000000-0000-0000-0000-000000000501")
APPROVAL_ID = UUID("00000000-0000-0000-0000-000000000601")


def test_action_policy_decision_is_immutable() -> None:
    decision = ActionPolicyDecision(
        action_policy_decision_id=DECISION_ID,
        action_proposal_id=PROPOSAL_ID,
        action_approval_id=APPROVAL_ID,
        decision=ActionPolicyOutcome.ALLOW,
        rule_id="allow",
        reason_code=ActionPolicyReasonCode.POLICY_ALLOWED,
        created_at=CREATED_AT,
    )

    with pytest.raises(FrozenInstanceError):
        decision.decision = ActionPolicyOutcome.DENY  # type: ignore[misc]


def test_allow_requires_approval_identity() -> None:
    with pytest.raises(ValueError, match="requires an ActionApproval"):
        ActionPolicyDecision(
            action_policy_decision_id=DECISION_ID,
            action_proposal_id=PROPOSAL_ID,
            action_approval_id=None,
            decision=ActionPolicyOutcome.ALLOW,
            rule_id="allow",
            reason_code=ActionPolicyReasonCode.POLICY_ALLOWED,
            created_at=CREATED_AT,
        )


def test_deny_may_omit_approval_identity() -> None:
    decision = ActionPolicyDecision(
        action_policy_decision_id=DECISION_ID,
        action_proposal_id=PROPOSAL_ID,
        action_approval_id=None,
        decision=ActionPolicyOutcome.DENY,
        rule_id="approval_presence",
        reason_code=ActionPolicyReasonCode.APPROVAL_MISSING,
        created_at=CREATED_AT,
    )

    assert decision.action_approval_id is None
    assert not hasattr(decision, "status")
    assert set(ActionPolicyOutcome) == {
        ActionPolicyOutcome.ALLOW,
        ActionPolicyOutcome.DENY,
    }


def test_deny_cannot_use_policy_allowed() -> None:
    with pytest.raises(ValueError, match="POLICY_ALLOWED"):
        ActionPolicyDecision(
            action_policy_decision_id=DECISION_ID,
            action_proposal_id=PROPOSAL_ID,
            action_approval_id=None,
            decision=ActionPolicyOutcome.DENY,
            rule_id="allow",
            reason_code=ActionPolicyReasonCode.POLICY_ALLOWED,
            created_at=CREATED_AT,
        )
