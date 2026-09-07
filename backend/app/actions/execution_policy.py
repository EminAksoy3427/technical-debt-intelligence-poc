from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.actions.contracts import (
    ActionPreparationContext,
    ActionProposalNotFound,
)
from app.domain.action_approvals import ActionApproval
from app.domain.action_policy import (
    ActionPolicyDecision,
    ActionPolicyOutcome,
    ActionPolicyReasonCode,
)
from app.domain.action_proposals import ActionProposal, ActionType
from app.infrastructure.database.action_approval_persistence import (
    load_action_approval_for_proposal,
)
from app.infrastructure.database.action_policy_persistence import (
    persist_action_policy_decision,
)
from app.infrastructure.database.action_proposal_persistence import load_action_proposal


@dataclass(frozen=True)
class ActionPolicyResult:
    decision: ActionPolicyOutcome
    rule_id: str
    reason_code: ActionPolicyReasonCode


def evaluate_action_execution_policy(
    *,
    action_type: str,
    proposal_fingerprint: str,
    target_repository_owner: str,
    target_repository_name: str,
    approval: ActionApproval | None,
    execution_enabled: bool,
    allowed_repository_owner: str,
    allowed_repository_name: str,
) -> ActionPolicyResult:
    """Evaluate trusted L4 execution policy in a fixed, deterministic order.

    Policy ALLOW means only that server policy would permit a future execution
    attempt. It is not GitHub success, TechnicalDebt closure, or Human Validation.
    """
    if not execution_enabled:
        return ActionPolicyResult(
            decision=ActionPolicyOutcome.DENY,
            rule_id="execution_enabled",
            reason_code=ActionPolicyReasonCode.EXECUTION_DISABLED,
        )
    if action_type != ActionType.CREATE_GITHUB_ISSUE.value:
        return ActionPolicyResult(
            decision=ActionPolicyOutcome.DENY,
            rule_id="action_type",
            reason_code=ActionPolicyReasonCode.ACTION_TYPE_NOT_ALLOWED,
        )
    if (
        target_repository_owner != allowed_repository_owner
        or target_repository_name != allowed_repository_name
        or not allowed_repository_owner.strip()
        or not allowed_repository_name.strip()
    ):
        return ActionPolicyResult(
            decision=ActionPolicyOutcome.DENY,
            rule_id="repository_allowlist",
            reason_code=ActionPolicyReasonCode.REPOSITORY_NOT_ALLOWLISTED,
        )
    if approval is None:
        return ActionPolicyResult(
            decision=ActionPolicyOutcome.DENY,
            rule_id="approval_presence",
            reason_code=ActionPolicyReasonCode.APPROVAL_MISSING,
        )
    if approval.payload_fingerprint != proposal_fingerprint:
        return ActionPolicyResult(
            decision=ActionPolicyOutcome.DENY,
            rule_id="fingerprint_binding",
            reason_code=ActionPolicyReasonCode.FINGERPRINT_MISMATCH,
        )
    return ActionPolicyResult(
        decision=ActionPolicyOutcome.ALLOW,
        rule_id="allow",
        reason_code=ActionPolicyReasonCode.POLICY_ALLOWED,
    )


def record_action_execution_policy_decision(
    session: Session,
    proposal: ActionProposal,
    approval: ActionApproval | None,
    allowed_target: ActionPreparationContext,
    execution_enabled: bool,
    *,
    clock: Callable[[], datetime] | None = None,
    new_id: Callable[[], UUID] | None = None,
) -> ActionPolicyDecision:
    """Append one policy evaluation from persisted/server-owned inputs.

    The caller owns the transaction. This helper flushes and does not commit.
    Package 5 should invoke this immediately before any future execution attempt.
    """
    now = clock or (lambda: datetime.now(UTC))
    next_id = new_id or uuid4
    result = evaluate_action_execution_policy(
        action_type=proposal.action_type.value,
        proposal_fingerprint=proposal.payload_fingerprint,
        target_repository_owner=proposal.target_repository_owner,
        target_repository_name=proposal.target_repository_name,
        approval=approval,
        execution_enabled=execution_enabled,
        allowed_repository_owner=allowed_target.target_repository_owner,
        allowed_repository_name=allowed_target.target_repository_name,
    )
    decision = ActionPolicyDecision(
        action_policy_decision_id=next_id(),
        action_proposal_id=proposal.action_proposal_id,
        action_approval_id=(
            None if approval is None else approval.action_approval_id
        ),
        decision=result.decision,
        rule_id=result.rule_id,
        reason_code=result.reason_code,
        created_at=now(),
    )
    persist_action_policy_decision(session, decision)
    return decision


def evaluate_persisted_action_execution_policy(
    session: Session,
    action_proposal_id: UUID,
    allowed_target: ActionPreparationContext,
    execution_enabled: bool,
    *,
    clock: Callable[[], datetime] | None = None,
    new_id: Callable[[], UUID] | None = None,
) -> ActionPolicyDecision:
    """Load trusted persisted facts, evaluate policy, and append the decision.

    The caller owns the transaction. Missing ActionProposal is a typed error.
    This is the internal Package 5 invocation boundary.
    """
    proposal = load_action_proposal(session, action_proposal_id)
    if proposal is None:
        raise ActionProposalNotFound("ActionProposal does not exist")
    approval = load_action_approval_for_proposal(session, action_proposal_id)
    return record_action_execution_policy_decision(
        session,
        proposal,
        approval,
        allowed_target,
        execution_enabled,
        clock=clock,
        new_id=new_id,
    )
