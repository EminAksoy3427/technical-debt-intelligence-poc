from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Unicode,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.candidate_models import CandidateModel


class HumanDecisionModel(Base):
    __tablename__ = "human_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision_type IN ('VALIDATE', 'REJECT', 'REQUEST_INFO')",
            name="ck_human_decisions_decision_type",
        ),
        CheckConstraint(
            "sequence_number >= 1",
            name="ck_human_decisions_sequence_number_positive",
        ),
        UniqueConstraint(
            "candidate_id",
            "sequence_number",
            name="uq_human_decisions_candidate_sequence",
        ),
    )

    human_decision_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "candidates.candidate_id",
            name="fk_human_decisions_candidate_id_candidates",
        ),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    decision_type: Mapped[str] = mapped_column(Unicode(16), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Unicode(2000), nullable=True)
    requested_information: Mapped[str | None] = mapped_column(
        Unicode(2000),
        nullable=True,
    )
    actor_reference: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    candidate: Mapped[CandidateModel] = relationship()
