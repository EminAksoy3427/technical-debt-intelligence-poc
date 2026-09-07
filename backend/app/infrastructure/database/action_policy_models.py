from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Unicode,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.action_approval_models import ActionApprovalModel
from app.infrastructure.database.action_proposal_models import ActionProposalModel
from app.infrastructure.database.base import Base


class ActionPolicyDecisionModel(Base):
    __tablename__ = "action_policy_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('ALLOW', 'DENY')",
            name="ck_action_policy_decisions_decision",
        ),
        CheckConstraint(
            "reason_code IN ("
            "'APPROVAL_MISSING', "
            "'FINGERPRINT_MISMATCH', "
            "'ACTION_TYPE_NOT_ALLOWED', "
            "'REPOSITORY_NOT_ALLOWLISTED', "
            "'EXECUTION_DISABLED', "
            "'POLICY_ALLOWED'"
            ")",
            name="ck_action_policy_decisions_reason_code",
        ),
        CheckConstraint(
            "decision <> 'ALLOW' OR action_approval_id IS NOT NULL",
            name="ck_action_policy_decisions_allow_requires_approval",
        ),
        Index(
            "ix_action_policy_decisions_action_proposal_id",
            "action_proposal_id",
        ),
    )

    action_policy_decision_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    action_proposal_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "action_proposals.action_proposal_id",
            name="fk_action_policy_decisions_action_proposal_id_action_proposals",
        ),
        nullable=False,
    )
    action_approval_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "action_approvals.action_approval_id",
            name="fk_action_policy_decisions_action_approval_id_action_approvals",
        ),
        nullable=True,
    )
    decision: Mapped[str] = mapped_column(Unicode(8), nullable=False)
    rule_id: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    reason_code: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    action_proposal: Mapped[ActionProposalModel] = relationship()
    action_approval: Mapped[ActionApprovalModel | None] = relationship()
