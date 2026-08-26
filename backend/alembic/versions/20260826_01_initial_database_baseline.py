"""Establish the initial database revision chain.

Revision ID: 20260826_01
Revises:
Create Date: 2026-08-26
"""

from collections.abc import Sequence

revision: str = "20260826_01"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Establish the baseline without creating application tables."""
    pass


def downgrade() -> None:
    """Remove the baseline revision without changing application schema."""
    pass
