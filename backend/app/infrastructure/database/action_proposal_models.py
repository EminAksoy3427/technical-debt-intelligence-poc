from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Unicode,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.technical_debt_models import TechnicalDebtModel


class ActionProposalModel(Base):
    __tablename__ = "action_proposals"
    __table_args__ = (
        CheckConstraint(
            "action_type IN ('CREATE_GITHUB_ISSUE')",
            name="ck_action_proposals_action_type",
        ),
        UniqueConstraint(
            "reconciliation_marker",
            name="uq_action_proposals_reconciliation_marker",
        ),
        Index("ix_action_proposals_technical_debt_id", "technical_debt_id"),
    )

    action_proposal_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    technical_debt_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "technical_debts.technical_debt_id",
            name="fk_action_proposals_technical_debt_id_technical_debts",
        ),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(Unicode(32), nullable=False)
    target_repository_owner: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    target_repository_name: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    title: Mapped[str] = mapped_column(Unicode(256), nullable=False)
    body: Mapped[str] = mapped_column(Unicode(4000), nullable=False)
    payload_fingerprint: Mapped[str] = mapped_column(Unicode(64), nullable=False)
    reconciliation_marker: Mapped[str] = mapped_column(Unicode(80), nullable=False)
    prepared_by: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    technical_debt: Mapped[TechnicalDebtModel] = relationship()
