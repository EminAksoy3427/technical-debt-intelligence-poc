"""Add idempotent ActionExecution persistence.

Revision ID: 20260907_03
Revises: 20260907_02
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260907_03"
down_revision: str | Sequence[str] | None = "20260907_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "action_executions",
        sa.Column("action_execution_id", sa.Uuid(), nullable=False),
        sa.Column("action_proposal_id", sa.Uuid(), nullable=False),
        sa.Column("technical_debt_id", sa.Uuid(), nullable=False),
        sa.Column("action_type", sa.Unicode(length=32), nullable=False),
        sa.Column("creation_policy_decision_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Unicode(length=16), nullable=False),
        sa.Column("external_issue_id", sa.BigInteger(), nullable=True),
        sa.Column("external_issue_number", sa.BigInteger(), nullable=True),
        sa.Column("external_issue_url", sa.Unicode(length=2048), nullable=True),
        sa.Column("safe_error_category", sa.Unicode(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "action_type IN ('CREATE_GITHUB_ISSUE')",
            name="ck_action_executions_action_type",
        ),
        sa.CheckConstraint(
            "status IN ('IN_PROGRESS', 'SUCCEEDED', 'FAILED', 'UNKNOWN')",
            name="ck_action_executions_status",
        ),
        sa.CheckConstraint(
            "safe_error_category IS NULL OR safe_error_category IN ("
            "'EXTERNAL_REJECTED', 'NOT_SENT', 'TRANSPORT_UNKNOWN')",
            name="ck_action_executions_safe_error_category",
        ),
        sa.ForeignKeyConstraint(
            ["action_proposal_id"],
            ["action_proposals.action_proposal_id"],
            name="fk_action_executions_action_proposal_id_action_proposals",
        ),
        sa.ForeignKeyConstraint(
            ["technical_debt_id"],
            ["technical_debts.technical_debt_id"],
            name="fk_action_executions_technical_debt_id_technical_debts",
        ),
        sa.ForeignKeyConstraint(
            ["creation_policy_decision_id"],
            ["action_policy_decisions.action_policy_decision_id"],
            name=(
                "fk_action_executions_creation_policy_decision_id_"
                "action_policy_decisions"
            ),
        ),
        sa.PrimaryKeyConstraint("action_execution_id", name="pk_action_executions"),
        sa.UniqueConstraint(
            "action_proposal_id", name="uq_action_executions_action_proposal_id"
        ),
    )
    op.create_index(
        "ix_action_executions_technical_debt_id",
        "action_executions",
        ["technical_debt_id"],
        unique=False,
    )
    predicate = sa.text("status IN ('IN_PROGRESS', 'SUCCEEDED', 'UNKNOWN')")
    op.create_index(
        "uq_action_executions_live_logical_action",
        "action_executions",
        ["technical_debt_id", "action_type"],
        unique=True,
        mssql_where=predicate,
        sqlite_where=predicate,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_action_executions_live_logical_action",
        table_name="action_executions",
    )
    op.drop_index(
        "ix_action_executions_technical_debt_id",
        table_name="action_executions",
    )
    op.drop_table("action_executions")
