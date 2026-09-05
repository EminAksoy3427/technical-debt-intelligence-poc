"""Add Agent investigation audit persistence.

Revision ID: 20260905_01
Revises: 20260831_01
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260905_01"
down_revision: str | Sequence[str] | None = "20260831_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the bounded Agent investigation audit aggregate."""
    op.create_table(
        "agent_runs",
        sa.Column("agent_run_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Unicode(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("structured_assessment", sa.JSON(), nullable=True),
        sa.Column("stop_reason", sa.Unicode(length=32), nullable=True),
        sa.CheckConstraint(
            "status IN ('CREATED', 'RUNNING', 'COMPLETED', 'ABSTAINED', 'FAILED')",
            name="ck_agent_runs_status",
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= COALESCE(started_at, created_at)",
            name="ck_agent_runs_completion_not_before_start",
        ),
        sa.CheckConstraint(
            "status NOT IN ('ABSTAINED', 'FAILED') OR stop_reason IS NOT NULL",
            name="ck_agent_runs_terminal_stop_reason",
        ),
        sa.CheckConstraint(
            "status <> 'COMPLETED' OR stop_reason IS NULL",
            name="ck_agent_runs_completed_without_stop_reason",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.candidate_id"],
            name="fk_agent_runs_candidate_id_candidates",
        ),
        sa.PrimaryKeyConstraint("agent_run_id", name="pk_agent_runs"),
    )
    op.create_index(
        "ix_agent_runs_candidate_id",
        "agent_runs",
        ["candidate_id"],
        unique=False,
    )
    op.create_table(
        "tool_executions",
        sa.Column("tool_execution_id", sa.Uuid(), nullable=False),
        sa.Column("agent_run_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("tool_id", sa.Unicode(length=100), nullable=False),
        sa.Column("tool_version", sa.Unicode(length=50), nullable=False),
        sa.Column("input_hash", sa.Unicode(length=64), nullable=False),
        sa.Column("safe_input_summary", sa.JSON(), nullable=False),
        sa.Column("status", sa.Unicode(length=32), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.Unicode(length=100), nullable=True),
        sa.Column("error_message", sa.Unicode(length=1000), nullable=True),
        sa.Column("result_references", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "status IN ('SUCCEEDED', 'DENIED', 'INVALID_ARGUMENTS', "
            "'TIMED_OUT', 'FAILED', 'UNAVAILABLE')",
            name="ck_tool_executions_status",
        ),
        sa.CheckConstraint(
            "sequence_number >= 1",
            name="ck_tool_executions_sequence_number_positive",
        ),
        sa.CheckConstraint(
            "duration_ms >= 0",
            name="ck_tool_executions_duration_non_negative",
        ),
        sa.CheckConstraint(
            "started_at IS NULL OR started_at >= requested_at",
            name="ck_tool_executions_start_not_before_request",
        ),
        sa.CheckConstraint(
            "finished_at >= COALESCE(started_at, requested_at)",
            name="ck_tool_executions_finish_not_before_start",
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id"],
            ["agent_runs.agent_run_id"],
            name="fk_tool_executions_agent_run_id_agent_runs",
        ),
        sa.PrimaryKeyConstraint("tool_execution_id", name="pk_tool_executions"),
        sa.UniqueConstraint(
            "agent_run_id",
            "sequence_number",
            name="uq_tool_executions_agent_run_sequence",
        ),
    )
    op.create_table(
        "policy_decisions",
        sa.Column("tool_execution_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.Unicode(length=8), nullable=False),
        sa.Column("requested_effect", sa.Unicode(length=8), nullable=False),
        sa.Column("requested_risk", sa.Unicode(length=16), nullable=False),
        sa.Column("required_scopes", sa.JSON(), nullable=False),
        sa.Column("granted_scopes", sa.JSON(), nullable=False),
        sa.Column("maximum_risk", sa.Unicode(length=16), nullable=False),
        sa.Column("rule_id", sa.Unicode(length=100), nullable=False),
        sa.Column("reason_code", sa.Unicode(length=100), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "decision IN ('ALLOW', 'DENY')",
            name="ck_policy_decisions_decision",
        ),
        sa.CheckConstraint(
            "requested_effect IN ('READ', 'WRITE')",
            name="ck_policy_decisions_requested_effect",
        ),
        sa.CheckConstraint(
            "requested_risk IN ('LOW', 'ELEVATED')",
            name="ck_policy_decisions_requested_risk",
        ),
        sa.CheckConstraint(
            "maximum_risk IN ('LOW', 'ELEVATED')",
            name="ck_policy_decisions_maximum_risk",
        ),
        sa.ForeignKeyConstraint(
            ["tool_execution_id"],
            ["tool_executions.tool_execution_id"],
            name="fk_policy_decisions_tool_execution_id_tool_executions",
        ),
        sa.PrimaryKeyConstraint("tool_execution_id", name="pk_policy_decisions"),
    )


def downgrade() -> None:
    """Remove the Agent investigation audit aggregate."""
    op.drop_table("policy_decisions")
    op.drop_table("tool_executions")
    op.drop_index("ix_agent_runs_candidate_id", table_name="agent_runs")
    op.drop_table("agent_runs")
