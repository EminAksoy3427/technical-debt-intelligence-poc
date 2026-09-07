"""Add append-only ActionApproval and ActionPolicyDecision persistence.

Revision ID: 20260907_02
Revises: 20260907_01
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260907_02"
down_revision: str | Sequence[str] | None = "20260907_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create L4 approval and dedicated action-policy audit tables."""
    op.create_table(
        "action_approvals",
        sa.Column("action_approval_id", sa.Uuid(), nullable=False),
        sa.Column("action_proposal_id", sa.Uuid(), nullable=False),
        sa.Column("payload_fingerprint", sa.Unicode(length=64), nullable=False),
        sa.Column("actor_reference", sa.Unicode(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["action_proposal_id"],
            ["action_proposals.action_proposal_id"],
            name="fk_action_approvals_action_proposal_id_action_proposals",
        ),
        sa.PrimaryKeyConstraint("action_approval_id", name="pk_action_approvals"),
        sa.UniqueConstraint(
            "action_proposal_id",
            name="uq_action_approvals_action_proposal_id",
        ),
    )
    op.create_table(
        "action_policy_decisions",
        sa.Column("action_policy_decision_id", sa.Uuid(), nullable=False),
        sa.Column("action_proposal_id", sa.Uuid(), nullable=False),
        sa.Column("action_approval_id", sa.Uuid(), nullable=True),
        sa.Column("decision", sa.Unicode(length=8), nullable=False),
        sa.Column("rule_id", sa.Unicode(length=100), nullable=False),
        sa.Column("reason_code", sa.Unicode(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "decision IN ('ALLOW', 'DENY')",
            name="ck_action_policy_decisions_decision",
        ),
        sa.CheckConstraint(
            "reason_code IN ("
            "'APPROVAL_MISSING', "
            "'FINGERPRINT_MISMATCH', "
            "'ACTION_TYPE_NOT_ALLOWED', "
            "'REPOSITORY_NOT_ALLOWLISTED', "
            "'EXECUTION_DISABLED', "
            "'POLICY_ALLOWED'"
            ")",
            name="ck_action_policy_decisions_reason_code",
        ),
        sa.CheckConstraint(
            "decision <> 'ALLOW' OR action_approval_id IS NOT NULL",
            name="ck_action_policy_decisions_allow_requires_approval",
        ),
        sa.ForeignKeyConstraint(
            ["action_proposal_id"],
            ["action_proposals.action_proposal_id"],
            name="fk_action_policy_decisions_action_proposal_id_action_proposals",
        ),
        sa.ForeignKeyConstraint(
            ["action_approval_id"],
            ["action_approvals.action_approval_id"],
            name="fk_action_policy_decisions_action_approval_id_action_approvals",
        ),
        sa.PrimaryKeyConstraint(
            "action_policy_decision_id",
            name="pk_action_policy_decisions",
        ),
    )
    op.create_index(
        "ix_action_policy_decisions_action_proposal_id",
        "action_policy_decisions",
        ["action_proposal_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove Package 4 objects without altering ActionProposal or TechnicalDebt."""
    op.drop_index(
        "ix_action_policy_decisions_action_proposal_id",
        table_name="action_policy_decisions",
    )
    op.drop_table("action_policy_decisions")
    op.drop_table("action_approvals")
