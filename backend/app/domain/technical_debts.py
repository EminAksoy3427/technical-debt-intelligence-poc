from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class TechnicalDebtLifecycleStatus(StrEnum):
    REGISTERED = "REGISTERED"


@dataclass(frozen=True)
class TechnicalDebt:
    """Provenance record created by a human VALIDATE decision."""

    technical_debt_id: UUID
    source_candidate_id: UUID
    creation_human_decision_id: UUID
    lifecycle_status: TechnicalDebtLifecycleStatus
    created_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.lifecycle_status, TechnicalDebtLifecycleStatus):
            raise ValueError("TechnicalDebt lifecycle status must be supported")
        if self.lifecycle_status is not TechnicalDebtLifecycleStatus.REGISTERED:
            raise ValueError("TechnicalDebt lifecycle status must be REGISTERED")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("TechnicalDebt created timestamp must be timezone-aware")
