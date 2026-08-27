"""Add the runtime enterprise estate foundation.

Revision ID: 20260827_01
Revises: 20260826_01
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_01"
down_revision: str | Sequence[str] | None = "20260826_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create canonical enterprise context tables."""
    op.create_table(
        "enterprise_assets",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("asset_key", sa.Unicode(length=100), nullable=False),
        sa.Column("asset_type", sa.Unicode(length=32), nullable=False),
        sa.Column("name", sa.Unicode(length=200), nullable=False),
        sa.Column("criticality", sa.Unicode(length=32), nullable=False),
        sa.Column("lifecycle_status", sa.Unicode(length=32), nullable=False),
        sa.CheckConstraint(
            "asset_type IN ('APPLICATION', 'SERVICE', 'REPOSITORY')",
            name="ck_enterprise_assets_asset_type",
        ),
        sa.CheckConstraint(
            "criticality IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_enterprise_assets_criticality",
        ),
        sa.CheckConstraint(
            "lifecycle_status IN ('PLANNED', 'ACTIVE', 'RETIRED')",
            name="ck_enterprise_assets_lifecycle_status",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_enterprise_assets"),
        sa.UniqueConstraint("asset_key", name="uq_enterprise_assets_asset_key"),
    )
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("team_key", sa.Unicode(length=100), nullable=False),
        sa.Column("name", sa.Unicode(length=200), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_teams"),
        sa.UniqueConstraint("team_key", name="uq_teams_team_key"),
    )
    op.create_table(
        "asset_ownerships",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("ownership_role", sa.Unicode(length=32), nullable=False),
        sa.CheckConstraint(
            "ownership_role IN ('PRIMARY', 'SUPPORTING')",
            name="ck_asset_ownerships_role",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["enterprise_assets.id"],
            name="fk_asset_ownerships_asset_id_enterprise_assets",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="fk_asset_ownerships_team_id_teams",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_asset_ownerships"),
        sa.UniqueConstraint(
            "asset_id",
            "team_id",
            "ownership_role",
            name="uq_asset_ownerships_asset_team_role",
        ),
    )
    op.create_table(
        "asset_relationships",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("source_asset_id", sa.Integer(), nullable=False),
        sa.Column("target_asset_id", sa.Integer(), nullable=False),
        sa.Column("relationship_type", sa.Unicode(length=32), nullable=False),
        sa.CheckConstraint(
            "relationship_type IN ('CONTAINS', 'IMPLEMENTED_BY', 'DEPENDS_ON')",
            name="ck_asset_relationships_type",
        ),
        sa.ForeignKeyConstraint(
            ["source_asset_id"],
            ["enterprise_assets.id"],
            name="fk_asset_relationships_source_asset_id_enterprise_assets",
        ),
        sa.ForeignKeyConstraint(
            ["target_asset_id"],
            ["enterprise_assets.id"],
            name="fk_asset_relationships_target_asset_id_enterprise_assets",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_asset_relationships"),
        sa.UniqueConstraint(
            "source_asset_id",
            "target_asset_id",
            "relationship_type",
            name="uq_asset_relationships_edge",
        ),
    )
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("incident_key", sa.Unicode(length=100), nullable=False),
        sa.Column(
            "primary_affected_asset_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column("severity", sa.Unicode(length=32), nullable=False),
        sa.Column("title", sa.Unicode(length=300), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_incidents_severity",
        ),
        sa.CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= started_at",
            name="ck_incidents_resolution_not_before_start",
        ),
        sa.ForeignKeyConstraint(
            ["primary_affected_asset_id"],
            ["enterprise_assets.id"],
            name="fk_incidents_primary_affected_asset_id_enterprise_assets",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_incidents"),
        sa.UniqueConstraint("incident_key", name="uq_incidents_incident_key"),
    )


def downgrade() -> None:
    """Remove canonical enterprise context tables."""
    op.drop_table("incidents")
    op.drop_table("asset_relationships")
    op.drop_table("asset_ownerships")
    op.drop_table("teams")
    op.drop_table("enterprise_assets")
