from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Unicode,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.candidate_models import CandidateModel


class AgentRunModel(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('CREATED', 'RUNNING', 'COMPLETED', 'ABSTAINED', 'FAILED')",
            name="ck_agent_runs_status",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= COALESCE(started_at, created_at)",
            name="ck_agent_runs_completion_not_before_start",
        ),
        CheckConstraint(
            "status NOT IN ('ABSTAINED', 'FAILED') OR stop_reason IS NOT NULL",
            name="ck_agent_runs_terminal_stop_reason",
        ),
        CheckConstraint(
            "status <> 'COMPLETED' OR stop_reason IS NULL",
            name="ck_agent_runs_completed_without_stop_reason",
        ),
        Index("ix_agent_runs_candidate_id", "candidate_id"),
    )

    agent_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "candidates.candidate_id",
            name="fk_agent_runs_candidate_id_candidates",
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Unicode(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    structured_assessment: Mapped[dict[str, object] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    stop_reason: Mapped[str | None] = mapped_column(Unicode(32), nullable=True)

    candidate: Mapped[CandidateModel] = relationship(backref="agent_runs")
    tool_executions: Mapped[list["ToolExecutionModel"]] = relationship(
        back_populates="agent_run",
        order_by="ToolExecutionModel.sequence_number",
    )


class ToolExecutionModel(Base):
    __tablename__ = "tool_executions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('SUCCEEDED', 'DENIED', 'INVALID_ARGUMENTS', "
            "'TIMED_OUT', 'FAILED', 'UNAVAILABLE')",
            name="ck_tool_executions_status",
        ),
        CheckConstraint(
            "sequence_number >= 1",
            name="ck_tool_executions_sequence_number_positive",
        ),
        CheckConstraint(
            "duration_ms >= 0",
            name="ck_tool_executions_duration_non_negative",
        ),
        CheckConstraint(
            "started_at IS NULL OR started_at >= requested_at",
            name="ck_tool_executions_start_not_before_request",
        ),
        CheckConstraint(
            "finished_at >= COALESCE(started_at, requested_at)",
            name="ck_tool_executions_finish_not_before_start",
        ),
        UniqueConstraint(
            "agent_run_id",
            "sequence_number",
            name="uq_tool_executions_agent_run_sequence",
        ),
    )

    tool_execution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    agent_run_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "agent_runs.agent_run_id",
            name="fk_tool_executions_agent_run_id_agent_runs",
        ),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_id: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    tool_version: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    input_hash: Mapped[str] = mapped_column(Unicode(64), nullable=False)
    safe_input_summary: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Unicode(32), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Unicode(1000), nullable=True)
    result_references: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        nullable=False,
    )

    agent_run: Mapped[AgentRunModel] = relationship(back_populates="tool_executions")
    policy_decision: Mapped["PolicyDecisionModel | None"] = relationship(
        back_populates="tool_execution",
        uselist=False,
    )


class PolicyDecisionModel(Base):
    __tablename__ = "policy_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('ALLOW', 'DENY')",
            name="ck_policy_decisions_decision",
        ),
        CheckConstraint(
            "requested_effect IN ('READ', 'WRITE')",
            name="ck_policy_decisions_requested_effect",
        ),
        CheckConstraint(
            "requested_risk IN ('LOW', 'ELEVATED')",
            name="ck_policy_decisions_requested_risk",
        ),
        CheckConstraint(
            "maximum_risk IN ('LOW', 'ELEVATED')",
            name="ck_policy_decisions_maximum_risk",
        ),
    )

    tool_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "tool_executions.tool_execution_id",
            name="fk_policy_decisions_tool_execution_id_tool_executions",
        ),
        primary_key=True,
    )
    decision: Mapped[str] = mapped_column(Unicode(8), nullable=False)
    requested_effect: Mapped[str] = mapped_column(Unicode(8), nullable=False)
    requested_risk: Mapped[str] = mapped_column(Unicode(16), nullable=False)
    required_scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    granted_scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    maximum_risk: Mapped[str] = mapped_column(Unicode(16), nullable=False)
    rule_id: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    reason_code: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    tool_execution: Mapped[ToolExecutionModel] = relationship(
        back_populates="policy_decision"
    )
