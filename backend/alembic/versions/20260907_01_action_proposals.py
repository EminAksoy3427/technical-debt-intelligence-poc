"""Add immutable ActionProposal persistence.

Revision ID: 20260907_01
Revises: 20260906_01
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260907_01"
down_revision: str | Sequence[str] | None = "20260906_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create append-only ActionProposal previews for REGISTERED TechnicalDebt."""
    op.create_table(
        "action_proposals",
        sa.Column("action_proposal_id", sa.Uuid(), nullable=False),
        sa.Column("technical_debt_id", sa.Uuid(), nullable=False),
        sa.Column("action_type", sa.Unicode(length=32), nullable=False),
        sa.Column("target_repository_owner", sa.Unicode(length=100), nullable=False),
        sa.Column("target_repository_name", sa.Unicode(length=100), nullable=False),
        sa.Column("title", sa.Unicode(length=256), nullable=False),
        sa.Column("body", sa.Unicode(length=4000), nullable=False),
        sa.Column("payload_fingerprint", sa.Unicode(length=64), nullable=False),
        sa.Column("reconciliation_marker", sa.Unicode(length=80), nullable=False),
        sa.Column("prepared_by", sa.Unicode(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action_type IN ('CREATE_GITHUB_ISSUE')",
            name="ck_action_proposals_action_type",
        ),
        sa.ForeignKeyConstraint(
            ["technical_debt_id"],
            ["technical_debts.technical_debt_id"],
            name="fk_action_proposals_technical_debt_id_technical_debts",
        ),
        sa.PrimaryKeyConstraint("action_proposal_id", name="pk_action_proposals"),
        sa.UniqueConstraint(
            "reconciliation_marker",
            name="uq_action_proposals_reconciliation_marker",
        ),
    )
    op.create_index(
        "ix_action_proposals_technical_debt_id",
        "action_proposals",
        ["technical_debt_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove ActionProposal persistence without altering TechnicalDebt."""
    op.drop_index(
        "ix_action_proposals_technical_debt_id",
        table_name="action_proposals",
    )
    op.drop_table("action_proposals")
