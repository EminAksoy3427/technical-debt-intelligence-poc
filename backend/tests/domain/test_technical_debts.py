from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.candidates import Candidate
from app.domain.human_decisions import HumanDecision
from app.domain.signals import Signal
from app.domain.technical_debts import TechnicalDebt, TechnicalDebtLifecycleStatus

CREATED_AT = datetime(2026, 9, 6, 16, 5, tzinfo=UTC)


def create_technical_debt(
    *,
    lifecycle_status: TechnicalDebtLifecycleStatus = (
        TechnicalDebtLifecycleStatus.REGISTERED
    ),
    created_at: datetime | None = None,
) -> TechnicalDebt:
    return TechnicalDebt(
        technical_debt_id=uuid4(),
        source_candidate_id=uuid4(),
        creation_human_decision_id=uuid4(),
        lifecycle_status=lifecycle_status,
        created_at=CREATED_AT if created_at is None else created_at,
    )


def test_technical_debt_starts_registered() -> None:
    debt = create_technical_debt()

    assert debt.lifecycle_status is TechnicalDebtLifecycleStatus.REGISTERED
    assert not hasattr(debt, "hypothesis")
    assert not hasattr(debt, "risk")
    assert not hasattr(debt, "effort")
    assert not hasattr(debt, "owner")


def test_technical_debt_is_distinct_from_candidate_and_signal() -> None:
    debt = create_technical_debt()

    assert not isinstance(debt, Candidate)
    assert not isinstance(debt, Signal)
    assert not isinstance(debt, HumanDecision)
    assert debt.technical_debt_id != debt.source_candidate_id
    assert debt.technical_debt_id != debt.creation_human_decision_id


def test_technical_debt_is_immutable() -> None:
    debt = create_technical_debt()

    with pytest.raises(FrozenInstanceError):
        debt.lifecycle_status = TechnicalDebtLifecycleStatus.REGISTERED  # type: ignore[misc]


def test_technical_debt_requires_timezone_aware_created_at() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        create_technical_debt(created_at=datetime(2026, 9, 6, 16, 5))


def test_technical_debt_rejects_unsupported_lifecycle_status() -> None:
    with pytest.raises(ValueError, match="lifecycle status"):
        create_technical_debt(lifecycle_status="ACTIVE")  # type: ignore[arg-type]
