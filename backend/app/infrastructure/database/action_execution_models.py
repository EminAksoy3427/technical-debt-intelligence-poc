from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Unicode,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.action_policy_models import ActionPolicyDecisionModel
from app.infrastructure.database.action_proposal_models import ActionProposalModel
from app.infrastructure.database.base import Base
from app.infrastructure.database.technical_debt_models import TechnicalDebtModel


class ActionExecutionModel(Base):
    __tablename__ = "action_executions"
    __table_args__ = (
        CheckConstraint(
            "action_type IN ('CREATE_GITHUB_ISSUE')",
            name="ck_action_executions_action_type",
        ),
        CheckConstraint(
            "status IN ('IN_PROGRESS', 'SUCCEEDED', 'FAILED', 'UNKNOWN')",
            name="ck_action_executions_status",
        ),
        CheckConstraint(
            "safe_error_category IS NULL OR safe_error_category IN ("
            "'EXTERNAL_REJECTED', 'NOT_SENT', 'TRANSPORT_UNKNOWN')",
            name="ck_action_executions_safe_error_category",
        ),
        UniqueConstraint(
            "action_proposal_id",
            name="uq_action_executions_action_proposal_id",
        ),
        Index("ix_action_executions_technical_debt_id", "technical_debt_id"),
        Index(
            "uq_action_executions_live_logical_action",
            "technical_debt_id",
            "action_type",
            unique=True,
            mssql_where=text("status IN ('IN_PROGRESS', 'SUCCEEDED', 'UNKNOWN')"),
            sqlite_where=text("status IN ('IN_PROGRESS', 'SUCCEEDED', 'UNKNOWN')"),
        ),
    )

    action_execution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True
    )
    action_proposal_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "action_proposals.action_proposal_id",
            name="fk_action_executions_action_proposal_id_action_proposals",
        ),
        nullable=False,
    )
    technical_debt_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "technical_debts.technical_debt_id",
            name="fk_action_executions_technical_debt_id_technical_debts",
        ),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(Unicode(32), nullable=False)
    creation_policy_decision_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "action_policy_decisions.action_policy_decision_id",
            name=(
                "fk_action_executions_creation_policy_decision_id_"
                "action_policy_decisions"
            ),
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Unicode(16), nullable=False)
    external_issue_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    external_issue_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    external_issue_url: Mapped[str | None] = mapped_column(Unicode(2048), nullable=True)
    safe_error_category: Mapped[str | None] = mapped_column(Unicode(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    action_proposal: Mapped[ActionProposalModel] = relationship()
    technical_debt: Mapped[TechnicalDebtModel] = relationship()
    creation_policy_decision: Mapped[ActionPolicyDecisionModel] = relationship()
