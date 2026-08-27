from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import CheckConstraint, UniqueConstraint

from app.infrastructure.database.base import Base
from app.infrastructure.database.enterprise_estate_models import (
    AssetOwnershipModel,
    AssetRelationshipModel,
    EnterpriseAssetModel,
    IncidentModel,
    TeamModel,
)

EXPECTED_TABLES = {
    "enterprise_assets",
    "teams",
    "asset_ownerships",
    "asset_relationships",
    "incidents",
}


def _unique_column_sets(table_name: str) -> set[frozenset[str]]:
    table = Base.metadata.tables[table_name]
    return {
        frozenset(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_metadata_contains_expected_enterprise_estate_tables() -> None:
    assert EXPECTED_TABLES <= set(Base.metadata.tables)


def test_enterprise_assets_use_stable_keys_and_contextual_criticality() -> None:
    table = EnterpriseAssetModel.__table__

    assert {
        "id",
        "asset_key",
        "asset_type",
        "name",
        "criticality",
        "lifecycle_status",
    } == set(table.columns.keys())
    assert frozenset({"asset_key"}) in _unique_column_sets("enterprise_assets")
    assert "risk" not in table.columns

    asset_type_constraint = next(
        constraint
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
        and constraint.name == "ck_enterprise_assets_asset_type"
    )
    asset_type_sql = str(asset_type_constraint.sqltext)
    assert "APPLICATION" in asset_type_sql
    assert "SERVICE" in asset_type_sql
    assert "REPOSITORY" in asset_type_sql


def test_asset_ownership_foreign_keys_and_duplicate_constraint() -> None:
    table = AssetOwnershipModel.__table__
    foreign_key_targets = {
        foreign_key.target_fullname for foreign_key in table.foreign_keys
    }

    assert foreign_key_targets == {"enterprise_assets.id", "teams.id"}
    assert frozenset({"asset_id", "team_id", "ownership_role"}) in _unique_column_sets(
        "asset_ownerships"
    )


def test_asset_relationship_is_a_unique_directed_edge() -> None:
    table = AssetRelationshipModel.__table__
    foreign_key_targets = [
        foreign_key.target_fullname for foreign_key in table.foreign_keys
    ]

    assert foreign_key_targets.count("enterprise_assets.id") == 2
    assert frozenset(
        {"source_asset_id", "target_asset_id", "relationship_type"}
    ) in _unique_column_sets("asset_relationships")


def test_incident_references_one_primary_affected_asset() -> None:
    table = IncidentModel.__table__

    assert frozenset({"incident_key"}) in _unique_column_sets("incidents")
    assert {foreign_key.target_fullname for foreign_key in table.foreign_keys} == {
        "enterprise_assets.id"
    }
    assert table.c.resolved_at.nullable is True


def test_orm_relationships_link_enterprise_context_models() -> None:
    asset = EnterpriseAssetModel(
        asset_key="asset-service",
        asset_type="SERVICE",
        name="Synthetic Service",
        criticality="HIGH",
        lifecycle_status="ACTIVE",
    )
    team = TeamModel(team_key="team-platform", name="Synthetic Platform Team")
    ownership = AssetOwnershipModel(
        asset=asset,
        team=team,
        ownership_role="PRIMARY",
    )
    dependency = EnterpriseAssetModel(
        asset_key="asset-repository",
        asset_type="REPOSITORY",
        name="Synthetic Repository",
        criticality="MEDIUM",
        lifecycle_status="ACTIVE",
    )
    edge = AssetRelationshipModel(
        source_asset=asset,
        target_asset=dependency,
        relationship_type="IMPLEMENTED_BY",
    )
    incident = IncidentModel(
        incident_key="incident-001",
        primary_affected_asset=asset,
        severity="HIGH",
        title="Synthetic service interruption",
        started_at=datetime(2026, 1, 15, 9, 0, tzinfo=UTC),
    )

    assert ownership.asset is asset
    assert ownership.team is team
    assert edge.source_asset is asset
    assert edge.target_asset is dependency
    assert incident.primary_affected_asset is asset


def test_alembic_revision_chains_from_baseline_and_compiles_for_mssql(
    monkeypatch,
) -> None:
    backend_root = Path(__file__).resolve().parents[3]
    config = Config(str(backend_root / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)
    head = scripts.get_revision(scripts.get_current_head())

    assert head.revision == "20260827_01"
    assert head.down_revision == "20260826_01"

    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="mssql",
        opts={"as_sql": True, "output_buffer": output},
    )
    monkeypatch.setattr(head.module, "op", Operations(context))

    head.module.upgrade()

    migration_sql = output.getvalue()
    for table_name in EXPECTED_TABLES:
        assert f"CREATE TABLE {table_name}" in migration_sql
