from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.technical_debts import TechnicalDebt, TechnicalDebtLifecycleStatus
from app.infrastructure.database.technical_debt_models import TechnicalDebtModel


def persist_technical_debt(session: Session, technical_debt: TechnicalDebt) -> None:
    """Insert one TechnicalDebt in the caller-owned transaction."""
    session.add(
        TechnicalDebtModel(
            technical_debt_id=technical_debt.technical_debt_id,
            source_candidate_id=technical_debt.source_candidate_id,
            creation_human_decision_id=technical_debt.creation_human_decision_id,
            lifecycle_status=technical_debt.lifecycle_status.value,
            created_at=technical_debt.created_at,
        )
    )
    session.flush()


def load_technical_debt(
    session: Session,
    technical_debt_id: UUID,
) -> TechnicalDebt | None:
    persisted = session.get(TechnicalDebtModel, technical_debt_id)
    if persisted is None:
        return None
    return _technical_debt_contract(persisted)


def load_technical_debt_for_candidate(
    session: Session,
    candidate_id: UUID,
) -> TechnicalDebt | None:
    persisted = session.scalar(
        select(TechnicalDebtModel).where(
            TechnicalDebtModel.source_candidate_id == candidate_id
        )
    )
    if persisted is None:
        return None
    return _technical_debt_contract(persisted)


def _technical_debt_contract(persisted: TechnicalDebtModel) -> TechnicalDebt:
    return TechnicalDebt(
        technical_debt_id=persisted.technical_debt_id,
        source_candidate_id=persisted.source_candidate_id,
        creation_human_decision_id=persisted.creation_human_decision_id,
        lifecycle_status=TechnicalDebtLifecycleStatus(persisted.lifecycle_status),
        created_at=_as_timezone_aware(persisted.created_at),
    )


def _as_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value
