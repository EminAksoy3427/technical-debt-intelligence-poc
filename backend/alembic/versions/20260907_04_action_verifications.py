"""Add append-only ActionVerification persistence.

Revision ID: 20260907_04
Revises: 20260907_03
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260907_04"
down_revision: str | Sequence[str] | None = "20260907_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "action_verifications",
        sa.Column("action_verification_id", sa.Uuid(), nullable=False),
        sa.Column("action_execution_id", sa.Uuid(), nullable=False),
        sa.Column("result", sa.Unicode(length=16), nullable=False),
        sa.Column("observed_issue_number", sa.BigInteger(), nullable=True),
        sa.Column("observed_issue_url", sa.Unicode(length=2048), nullable=True),
        sa.Column("safe_reason_code", sa.Unicode(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "result IN ('PASS', 'FAIL', 'UNAVAILABLE')",
            name="ck_action_verifications_result",
        ),
        sa.CheckConstraint(
            "safe_reason_code IS NULL OR safe_reason_code IN ("
            "'TITLE_MISMATCH', 'FINGERPRINT_MISMATCH', 'MARKER_MISSING', "
            "'PULL_REQUEST', 'REFERENCE_MISMATCH', 'TRANSPORT_UNAVAILABLE')",
            name="ck_action_verifications_safe_reason_code",
        ),
        sa.ForeignKeyConstraint(
            ["action_execution_id"],
            ["action_executions.action_execution_id"],
            name="fk_action_verifications_action_execution_id_action_executions",
        ),
        sa.PrimaryKeyConstraint(
            "action_verification_id", name="pk_action_verifications"
        ),
    )
    op.create_index(
        "ix_action_verifications_action_execution_id",
        "action_verifications",
        ["action_execution_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_action_verifications_action_execution_id",
        table_name="action_verifications",
    )
    op.drop_table("action_verifications")
