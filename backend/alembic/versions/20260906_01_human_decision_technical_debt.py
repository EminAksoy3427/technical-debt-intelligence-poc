"""Add HumanDecision and TechnicalDebt persistence.

Revision ID: 20260906_01
Revises: 20260905_01
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260906_01"
down_revision: str | Sequence[str] | None = "20260905_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create append-only HumanDecision history and VALIDATE TechnicalDebt."""
    op.create_table(
        "human_decisions",
        sa.Column("human_decision_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("decision_type", sa.Unicode(length=16), nullable=False),
        sa.Column("rationale", sa.Unicode(length=2000), nullable=True),
        sa.Column("requested_information", sa.Unicode(length=2000), nullable=True),
        sa.Column("actor_reference", sa.Unicode(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "decision_type IN ('VALIDATE', 'REJECT', 'REQUEST_INFO')",
            name="ck_human_decisions_decision_type",
        ),
        sa.CheckConstraint(
            "sequence_number >= 1",
            name="ck_human_decisions_sequence_number_positive",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.candidate_id"],
            name="fk_human_decisions_candidate_id_candidates",
        ),
        sa.PrimaryKeyConstraint("human_decision_id", name="pk_human_decisions"),
        sa.UniqueConstraint(
            "candidate_id",
            "sequence_number",
            name="uq_human_decisions_candidate_sequence",
        ),
    )
    op.create_table(
        "technical_debts",
        sa.Column("technical_debt_id", sa.Uuid(), nullable=False),
        sa.Column("source_candidate_id", sa.Uuid(), nullable=False),
        sa.Column("creation_human_decision_id", sa.Uuid(), nullable=False),
        sa.Column("lifecycle_status", sa.Unicode(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "lifecycle_status IN ('REGISTERED')",
            name="ck_technical_debts_lifecycle_status",
        ),
        sa.ForeignKeyConstraint(
            ["source_candidate_id"],
            ["candidates.candidate_id"],
            name="fk_technical_debts_source_candidate_id_candidates",
        ),
        sa.ForeignKeyConstraint(
            ["creation_human_decision_id"],
            ["human_decisions.human_decision_id"],
            name="fk_technical_debts_creation_human_decision_id_human_decisions",
        ),
        sa.PrimaryKeyConstraint("technical_debt_id", name="pk_technical_debts"),
        sa.UniqueConstraint(
            "source_candidate_id",
            name="uq_technical_debts_source_candidate_id",
        ),
        sa.UniqueConstraint(
            "creation_human_decision_id",
            name="uq_technical_debts_creation_human_decision_id",
        ),
    )


def downgrade() -> None:
    """Remove TechnicalDebt before HumanDecision due to foreign keys."""
    op.drop_table("technical_debts")
    op.drop_table("human_decisions")
