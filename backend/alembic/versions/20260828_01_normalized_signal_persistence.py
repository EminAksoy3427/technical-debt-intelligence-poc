"""Add normalized Signal and Evidence persistence.

Revision ID: 20260828_01
Revises: 20260827_01
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260828_01"
down_revision: str | Sequence[str] | None = "20260827_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create normalized Signal and Evidence tables."""
    op.create_table(
        "signals",
        sa.Column("signal_id", sa.Uuid(), nullable=False),
        sa.Column("source_system", sa.Unicode(length=100), nullable=False),
        sa.Column("source_record_id", sa.Unicode(length=500), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signal_type", sa.Unicode(length=100), nullable=False),
        sa.Column("affected_asset_id", sa.Integer(), nullable=False),
        sa.Column("severity", sa.Unicode(length=32), nullable=True),
        sa.ForeignKeyConstraint(
            ["affected_asset_id"],
            ["enterprise_assets.id"],
            name="fk_signals_affected_asset_id_enterprise_assets",
        ),
        sa.PrimaryKeyConstraint("signal_id", name="pk_signals"),
        sa.UniqueConstraint(
            "source_system",
            "source_record_id",
            name="uq_signals_source_system_source_record_id",
        ),
    )
    op.create_table(
        "evidence",
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("signal_id", sa.Uuid(), nullable=False),
        sa.Column("source_system", sa.Unicode(length=100), nullable=False),
        sa.Column("source_reference", sa.Unicode(length=1000), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference_uri", sa.Unicode(length=2048), nullable=True),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.signal_id"],
            name="fk_evidence_signal_id_signals",
        ),
        sa.PrimaryKeyConstraint("evidence_id", name="pk_evidence"),
    )


def downgrade() -> None:
    """Remove normalized Signal and Evidence tables."""
    op.drop_table("evidence")
    op.drop_table("signals")
