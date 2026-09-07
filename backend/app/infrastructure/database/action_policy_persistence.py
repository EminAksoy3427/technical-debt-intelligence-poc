from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.action_policy import (
    ActionPolicyDecision,
    ActionPolicyOutcome,
    ActionPolicyReasonCode,
)
from app.infrastructure.database.action_policy_models import ActionPolicyDecisionModel


def persist_action_policy_decision(
    session: Session,
    decision: ActionPolicyDecision,
) -> None:
    """Insert one append-only ActionPolicyDecision in the caller-owned transaction."""
    session.add(
        ActionPolicyDecisionModel(
            action_policy_decision_id=decision.action_policy_decision_id,
            action_proposal_id=decision.action_proposal_id,
            action_approval_id=decision.action_approval_id,
            decision=decision.decision.value,
            rule_id=decision.rule_id,
            reason_code=decision.reason_code.value,
            created_at=decision.created_at,
        )
    )
    session.flush()


def load_action_policy_decision(
    session: Session,
    action_policy_decision_id: UUID,
) -> ActionPolicyDecision | None:
    persisted = session.get(ActionPolicyDecisionModel, action_policy_decision_id)
    if persisted is None:
        return None
    return _action_policy_decision_contract(persisted)


def list_action_policy_decisions_for_proposal(
    session: Session,
    action_proposal_id: UUID,
) -> tuple[ActionPolicyDecision, ...]:
    """Load policy evaluations for one ActionProposal, oldest then newest."""
    persisted = session.scalars(
        select(ActionPolicyDecisionModel)
        .where(ActionPolicyDecisionModel.action_proposal_id == action_proposal_id)
        .order_by(
            ActionPolicyDecisionModel.created_at.asc(),
            ActionPolicyDecisionModel.action_policy_decision_id.asc(),
        )
    ).all()
    return tuple(_action_policy_decision_contract(item) for item in persisted)


def _action_policy_decision_contract(
    persisted: ActionPolicyDecisionModel,
) -> ActionPolicyDecision:
    return ActionPolicyDecision(
        action_policy_decision_id=persisted.action_policy_decision_id,
        action_proposal_id=persisted.action_proposal_id,
        action_approval_id=persisted.action_approval_id,
        decision=ActionPolicyOutcome(persisted.decision),
        rule_id=persisted.rule_id,
        reason_code=ActionPolicyReasonCode(persisted.reason_code),
        created_at=_as_timezone_aware(persisted.created_at),
    )


def _as_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value
