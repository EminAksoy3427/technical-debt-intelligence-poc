from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from alembic import command
from app.core.config import Settings
from app.domain.synthetic_enterprise_estate import (
    SYNTHETIC_ASSET_OWNERSHIPS,
    SYNTHETIC_ASSET_RELATIONSHIPS,
    SYNTHETIC_ENTERPRISE_ASSETS,
    SYNTHETIC_INCIDENTS,
    SYNTHETIC_TEAMS,
)
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.database.enterprise_estate_models import (
    AssetOwnershipModel,
    AssetRelationshipModel,
    EnterpriseAssetModel,
    IncidentModel,
    TeamModel,
)
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate


def _logical_snapshot(session: Session) -> tuple[object, ...]:
    asset_keys = [asset.asset_key for asset in SYNTHETIC_ENTERPRISE_ASSETS]
    team_keys = [team.team_key for team in SYNTHETIC_TEAMS]
    incident_keys = [incident.incident_key for incident in SYNTHETIC_INCIDENTS]

    assets = tuple(
        sorted(
            session.execute(
                select(
                    EnterpriseAssetModel.asset_key,
                    EnterpriseAssetModel.asset_type,
                    EnterpriseAssetModel.name,
                    EnterpriseAssetModel.criticality,
                    EnterpriseAssetModel.lifecycle_status,
                ).where(EnterpriseAssetModel.asset_key.in_(asset_keys))
            ).all()
        )
    )
    teams = tuple(
        sorted(
            session.execute(
                select(TeamModel.team_key, TeamModel.name).where(
                    TeamModel.team_key.in_(team_keys)
                )
            ).all()
        )
    )
    ownerships = tuple(
        sorted(
            session.execute(
                select(
                    EnterpriseAssetModel.asset_key,
                    TeamModel.team_key,
                    AssetOwnershipModel.ownership_role,
                )
                .join(
                    AssetOwnershipModel,
                    AssetOwnershipModel.asset_id == EnterpriseAssetModel.id,
                )
                .join(TeamModel, AssetOwnershipModel.team_id == TeamModel.id)
                .where(
                    EnterpriseAssetModel.asset_key.in_(asset_keys),
                    TeamModel.team_key.in_(team_keys),
                )
            ).all()
        )
    )
    source_asset = aliased(EnterpriseAssetModel)
    target_asset = aliased(EnterpriseAssetModel)
    relationships = tuple(
        sorted(
            session.execute(
                select(
                    source_asset.asset_key,
                    target_asset.asset_key,
                    AssetRelationshipModel.relationship_type,
                )
                .join(
                    source_asset,
                    AssetRelationshipModel.source_asset_id == source_asset.id,
                )
                .join(
                    target_asset,
                    AssetRelationshipModel.target_asset_id == target_asset.id,
                )
                .where(
                    source_asset.asset_key.in_(asset_keys),
                    target_asset.asset_key.in_(asset_keys),
                )
            ).all()
        )
    )
    incidents = tuple(
        sorted(
            session.execute(
                select(
                    IncidentModel.incident_key,
                    EnterpriseAssetModel.asset_key,
                    IncidentModel.severity,
                    IncidentModel.title,
                    IncidentModel.started_at,
                    IncidentModel.resolved_at,
                )
                .join(
                    EnterpriseAssetModel,
                    IncidentModel.primary_affected_asset_id == EnterpriseAssetModel.id,
                )
                .where(IncidentModel.incident_key.in_(incident_keys))
            ).all()
        )
    )

    return assets, teams, ownerships, relationships, incidents


def _seed_controlled_counts(session: Session) -> tuple[int, int, int, int, int]:
    snapshot = _logical_snapshot(session)
    return tuple(len(records) for records in snapshot)  # type: ignore[return-value]


@pytest.mark.integration
def test_mssql_seed_is_idempotent_with_a_stable_logical_snapshot() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")

    backend_root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_root / "alembic.ini")), "head")
    engine = create_database_engine(app_settings)
    try:
        with Session(engine) as session:
            transaction = session.begin()
            try:
                seed_enterprise_estate(session)
                snapshot_after_first_seed = _logical_snapshot(session)
                counts_after_first_seed = _seed_controlled_counts(session)

                seed_enterprise_estate(session)
                snapshot_after_second_seed = _logical_snapshot(session)
                counts_after_second_seed = _seed_controlled_counts(session)
            finally:
                transaction.rollback()
    finally:
        engine.dispose()

    assert snapshot_after_first_seed == snapshot_after_second_seed
    assert counts_after_first_seed == counts_after_second_seed
    assert counts_after_second_seed == (
        len(SYNTHETIC_ENTERPRISE_ASSETS),
        len(SYNTHETIC_TEAMS),
        len(SYNTHETIC_ASSET_OWNERSHIPS),
        len(SYNTHETIC_ASSET_RELATIONSHIPS),
        len(SYNTHETIC_INCIDENTS),
    )
