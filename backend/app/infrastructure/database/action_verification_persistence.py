from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.action_verifications import (
    ActionVerification,
    ActionVerificationReasonCode,
    ActionVerificationResult,
)
from app.infrastructure.database.action_execution_models import ActionExecutionModel
from app.infrastructure.database.action_verification_models import (
    ActionVerificationModel,
)


def persist_action_verification(
    session: Session,
    verification: ActionVerification,
) -> None:
    """Insert one append-only ActionVerification in the caller-owned transaction."""
    session.add(
        ActionVerificationModel(
            action_verification_id=verification.action_verification_id,
            action_execution_id=verification.action_execution_id,
            result=verification.result.value,
            observed_issue_number=verification.observed_issue_number,
            observed_issue_url=verification.observed_issue_url,
            safe_reason_code=(
                None
                if verification.safe_reason_code is None
                else verification.safe_reason_code.value
            ),
            created_at=verification.created_at,
        )
    )
    session.flush()


def load_action_verification(
    session: Session,
    action_verification_id: UUID,
) -> ActionVerification | None:
    persisted = session.get(ActionVerificationModel, action_verification_id)
    return None if persisted is None else _verification_contract(persisted)


def list_action_verifications_for_technical_debt(
    session: Session,
    technical_debt_id: UUID,
) -> tuple[ActionVerification, ...]:
    """Load ActionVerifications for one TechnicalDebt, oldest then newest."""
    persisted = session.scalars(
        select(ActionVerificationModel)
        .join(
            ActionExecutionModel,
            ActionVerificationModel.action_execution_id
            == ActionExecutionModel.action_execution_id,
        )
        .where(ActionExecutionModel.technical_debt_id == technical_debt_id)
        .order_by(
            ActionVerificationModel.created_at.asc(),
            ActionVerificationModel.action_verification_id.asc(),
        )
    ).all()
    return tuple(_verification_contract(item) for item in persisted)


def _verification_contract(persisted: ActionVerificationModel) -> ActionVerification:
    return ActionVerification(
        action_verification_id=persisted.action_verification_id,
        action_execution_id=persisted.action_execution_id,
        result=ActionVerificationResult(persisted.result),
        observed_issue_number=persisted.observed_issue_number,
        observed_issue_url=persisted.observed_issue_url,
        safe_reason_code=(
            None
            if persisted.safe_reason_code is None
            else ActionVerificationReasonCode(persisted.safe_reason_code)
        ),
        created_at=_as_timezone_aware(persisted.created_at),
    )


def _as_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value
