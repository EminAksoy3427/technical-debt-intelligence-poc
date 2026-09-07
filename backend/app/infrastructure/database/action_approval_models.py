from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Unicode,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.action_proposal_models import ActionProposalModel
from app.infrastructure.database.base import Base


class ActionApprovalModel(Base):
    __tablename__ = "action_approvals"
    __table_args__ = (
        UniqueConstraint(
            "action_proposal_id",
            name="uq_action_approvals_action_proposal_id",
        ),
    )

    action_approval_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    action_proposal_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "action_proposals.action_proposal_id",
            name="fk_action_approvals_action_proposal_id_action_proposals",
        ),
        nullable=False,
    )
    payload_fingerprint: Mapped[str] = mapped_column(Unicode(64), nullable=False)
    actor_reference: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    action_proposal: Mapped[ActionProposalModel] = relationship()
