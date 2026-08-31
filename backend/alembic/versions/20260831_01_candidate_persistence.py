"""Add Candidate persistence.

Revision ID: 20260831_01
Revises: 20260828_01
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260831_01"
down_revision: str | Sequence[str] | None = "20260828_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create Candidate snapshots and normalized Signal membership."""
    op.create_table(
        "candidates",
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("canonical_asset_id", sa.Integer(), nullable=False),
        sa.Column("hypothesis", sa.Unicode(length=1000), nullable=False),
        sa.Column("correlation_rationale", sa.Unicode(length=2000), nullable=False),
        sa.ForeignKeyConstraint(
            ["canonical_asset_id"],
            ["enterprise_assets.id"],
            name="fk_candidates_canonical_asset_id_enterprise_assets",
        ),
        sa.PrimaryKeyConstraint("candidate_id", name="pk_candidates"),
    )
    op.create_table(
        "candidate_signals",
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("signal_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.candidate_id"],
            name="fk_candidate_signals_candidate_id_candidates",
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.signal_id"],
            name="fk_candidate_signals_signal_id_signals",
        ),
        sa.PrimaryKeyConstraint(
            "candidate_id",
            "signal_id",
            name="pk_candidate_signals",
        ),
    )


def downgrade() -> None:
    """Remove Candidate persistence structures."""
    op.drop_table("candidate_signals")
    op.drop_table("candidates")
