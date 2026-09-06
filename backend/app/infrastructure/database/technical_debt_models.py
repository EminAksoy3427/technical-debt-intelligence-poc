from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Unicode,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.candidate_models import CandidateModel
from app.infrastructure.database.human_decision_models import HumanDecisionModel


class TechnicalDebtModel(Base):
    __tablename__ = "technical_debts"
    __table_args__ = (
        CheckConstraint(
            "lifecycle_status IN ('REGISTERED')",
            name="ck_technical_debts_lifecycle_status",
        ),
        UniqueConstraint(
            "source_candidate_id",
            name="uq_technical_debts_source_candidate_id",
        ),
        UniqueConstraint(
            "creation_human_decision_id",
            name="uq_technical_debts_creation_human_decision_id",
        ),
    )

    technical_debt_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    source_candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "candidates.candidate_id",
            name="fk_technical_debts_source_candidate_id_candidates",
        ),
        nullable=False,
    )
    creation_human_decision_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "human_decisions.human_decision_id",
            name="fk_technical_debts_creation_human_decision_id_human_decisions",
        ),
        nullable=False,
    )
    lifecycle_status: Mapped[str] = mapped_column(Unicode(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    source_candidate: Mapped[CandidateModel] = relationship()
    creation_human_decision: Mapped[HumanDecisionModel] = relationship()
