from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.action_executions import (
    ActionExecution,
    ActionExecutionErrorCategory,
    ActionExecutionStatus,
)
from app.domain.action_policy import ActionPolicyOutcome
from app.domain.action_proposals import ActionType
from app.infrastructure.database.action_execution_models import ActionExecutionModel
from app.infrastructure.database.action_policy_models import ActionPolicyDecisionModel

OCCUPYING_EXECUTION_STATUSES = (
    ActionExecutionStatus.IN_PROGRESS.value,
    ActionExecutionStatus.SUCCEEDED.value,
    ActionExecutionStatus.UNKNOWN.value,
)


def persist_action_execution(session: Session, execution: ActionExecution) -> None:
    """Insert an IN_PROGRESS execution bound to a persisted ALLOW decision."""
    if execution.status is not ActionExecutionStatus.IN_PROGRESS:
        raise ValueError("A new ActionExecution must be IN_PROGRESS")
    policy = session.get(
        ActionPolicyDecisionModel,
        execution.creation_policy_decision_id,
    )
    if policy is None or policy.decision != ActionPolicyOutcome.ALLOW.value:
        raise ValueError("ActionExecution creation requires a persisted ALLOW decision")
    if policy.action_proposal_id != execution.action_proposal_id:
        raise ValueError("ALLOW decision must authorize the same ActionProposal")
    session.add(_execution_model(execution))
    session.flush()


def finalize_action_execution(session: Session, execution: ActionExecution) -> None:
    """Apply the sole Package 5 transition from IN_PROGRESS to a terminal state."""
    if execution.status is ActionExecutionStatus.IN_PROGRESS:
        raise ValueError("Finalization requires a terminal ActionExecution")
    persisted = session.get(ActionExecutionModel, execution.action_execution_id)
    if persisted is None:
        raise ValueError("ActionExecution does not exist")
    if persisted.status != ActionExecutionStatus.IN_PROGRESS.value:
        raise ValueError("Only IN_PROGRESS ActionExecution may be finalized")
    persisted.status = execution.status.value
    persisted.external_issue_id = execution.external_issue_id
    persisted.external_issue_number = execution.external_issue_number
    persisted.external_issue_url = execution.external_issue_url
    persisted.safe_error_category = (
        None
        if execution.safe_error_category is None
        else execution.safe_error_category.value
    )
    persisted.completed_at = execution.completed_at
    session.flush()


def reconcile_unknown_execution_success(
    session: Session,
    execution: ActionExecution,
) -> None:
    """Apply the sole Package 6 UNKNOWN → SUCCEEDED transition after marker proof."""
    if execution.status is not ActionExecutionStatus.SUCCEEDED:
        raise ValueError("UNKNOWN reconciliation requires a SUCCEEDED ActionExecution")
    persisted = session.get(ActionExecutionModel, execution.action_execution_id)
    if persisted is None:
        raise ValueError("ActionExecution does not exist")
    if persisted.status != ActionExecutionStatus.UNKNOWN.value:
        raise ValueError("Only UNKNOWN ActionExecution may be reconciled to SUCCEEDED")
    persisted.status = ActionExecutionStatus.SUCCEEDED.value
    persisted.external_issue_id = execution.external_issue_id
    persisted.external_issue_number = execution.external_issue_number
    persisted.external_issue_url = execution.external_issue_url
    persisted.safe_error_category = None
    persisted.completed_at = execution.completed_at
    session.flush()


def lock_action_execution(
    session: Session,
    action_execution_id: UUID,
) -> ActionExecution | None:
    """Load one ActionExecution with MSSQL UPDLOCK, HOLDLOCK on that dialect."""
    persisted = session.scalar(
        select(ActionExecutionModel)
        .where(ActionExecutionModel.action_execution_id == action_execution_id)
        .with_hint(
            ActionExecutionModel,
            "WITH (UPDLOCK, HOLDLOCK)",
            dialect_name="mssql",
        )
    )
    return None if persisted is None else _execution_contract(persisted)


def load_action_execution(
    session: Session,
    action_execution_id: UUID,
) -> ActionExecution | None:
    persisted = session.get(ActionExecutionModel, action_execution_id)
    return None if persisted is None else _execution_contract(persisted)


def load_action_execution_for_proposal(
    session: Session,
    action_proposal_id: UUID,
) -> ActionExecution | None:
    persisted = session.scalar(
        select(ActionExecutionModel).where(
            ActionExecutionModel.action_proposal_id == action_proposal_id
        )
    )
    return None if persisted is None else _execution_contract(persisted)


def load_occupying_action_execution(
    session: Session,
    technical_debt_id: UUID,
    action_type: ActionType,
) -> ActionExecution | None:
    persisted = session.scalar(
        select(ActionExecutionModel)
        .where(ActionExecutionModel.technical_debt_id == technical_debt_id)
        .where(ActionExecutionModel.action_type == action_type.value)
        .where(ActionExecutionModel.status.in_(OCCUPYING_EXECUTION_STATUSES))
    )
    return None if persisted is None else _execution_contract(persisted)


def list_action_executions_for_technical_debt(
    session: Session,
    technical_debt_id: UUID,
) -> tuple[ActionExecution, ...]:
    persisted = session.scalars(
        select(ActionExecutionModel)
        .where(ActionExecutionModel.technical_debt_id == technical_debt_id)
        .order_by(
            ActionExecutionModel.started_at.asc(),
            ActionExecutionModel.action_execution_id.asc(),
        )
    ).all()
    return tuple(_execution_contract(item) for item in persisted)


def _execution_model(execution: ActionExecution) -> ActionExecutionModel:
    return ActionExecutionModel(
        action_execution_id=execution.action_execution_id,
        action_proposal_id=execution.action_proposal_id,
        technical_debt_id=execution.technical_debt_id,
        action_type=execution.action_type.value,
        creation_policy_decision_id=execution.creation_policy_decision_id,
        status=execution.status.value,
        external_issue_id=execution.external_issue_id,
        external_issue_number=execution.external_issue_number,
        external_issue_url=execution.external_issue_url,
        safe_error_category=(
            None
            if execution.safe_error_category is None
            else execution.safe_error_category.value
        ),
        started_at=execution.started_at,
        completed_at=execution.completed_at,
    )


def _execution_contract(persisted: ActionExecutionModel) -> ActionExecution:
    return ActionExecution(
        action_execution_id=persisted.action_execution_id,
        action_proposal_id=persisted.action_proposal_id,
        technical_debt_id=persisted.technical_debt_id,
        action_type=ActionType(persisted.action_type),
        creation_policy_decision_id=persisted.creation_policy_decision_id,
        status=ActionExecutionStatus(persisted.status),
        external_issue_id=persisted.external_issue_id,
        external_issue_number=persisted.external_issue_number,
        external_issue_url=persisted.external_issue_url,
        safe_error_category=(
            None
            if persisted.safe_error_category is None
            else ActionExecutionErrorCategory(persisted.safe_error_category)
        ),
        started_at=_as_timezone_aware(persisted.started_at),
        completed_at=(
            None
            if persisted.completed_at is None
            else _as_timezone_aware(persisted.completed_at)
        ),
    )


def _as_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value
