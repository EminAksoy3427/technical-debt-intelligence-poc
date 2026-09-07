from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Unicode,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.action_execution_models import ActionExecutionModel
from app.infrastructure.database.base import Base


class ActionVerificationModel(Base):
    __tablename__ = "action_verifications"
    __table_args__ = (
        CheckConstraint(
            "result IN ('PASS', 'FAIL', 'UNAVAILABLE')",
            name="ck_action_verifications_result",
        ),
        CheckConstraint(
            "safe_reason_code IS NULL OR safe_reason_code IN ("
            "'TITLE_MISMATCH', 'FINGERPRINT_MISMATCH', 'MARKER_MISSING', "
            "'PULL_REQUEST', 'REFERENCE_MISMATCH', 'TRANSPORT_UNAVAILABLE')",
            name="ck_action_verifications_safe_reason_code",
        ),
        Index(
            "ix_action_verifications_action_execution_id",
            "action_execution_id",
        ),
    )

    action_verification_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True
    )
    action_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "action_executions.action_execution_id",
            name="fk_action_verifications_action_execution_id_action_executions",
        ),
        nullable=False,
    )
    result: Mapped[str] = mapped_column(Unicode(16), nullable=False)
    observed_issue_number: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    observed_issue_url: Mapped[str | None] = mapped_column(
        Unicode(2048), nullable=True
    )
    safe_reason_code: Mapped[str | None] = mapped_column(Unicode(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    action_execution: Mapped[ActionExecutionModel] = relationship()
