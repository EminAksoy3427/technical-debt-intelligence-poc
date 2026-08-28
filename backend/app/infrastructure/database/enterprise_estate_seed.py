from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enterprise_estate import (
    EnterpriseAsset,
    Incident,
    Team,
)
from app.domain.synthetic_enterprise_estate import (
    SYNTHETIC_ASSET_OWNERSHIPS,
    SYNTHETIC_ASSET_RELATIONSHIPS,
    SYNTHETIC_ENTERPRISE_ASSETS,
    SYNTHETIC_INCIDENTS,
    SYNTHETIC_TEAMS,
)
from app.infrastructure.database.enterprise_estate_models import (
    AssetOwnershipModel,
    AssetRelationshipModel,
    EnterpriseAssetModel,
    IncidentModel,
    TeamModel,
)


def _get_or_create(
    session: Session,
    model_type: type[EnterpriseAssetModel] | type[TeamModel] | type[IncidentModel],
    key_column: object,
    key: str,
    factory: Callable[[], EnterpriseAssetModel | TeamModel | IncidentModel],
) -> EnterpriseAssetModel | TeamModel | IncidentModel:
    model = session.scalar(select(model_type).where(key_column == key))
    if model is None:
        model = factory()
        session.add(model)
    return model


def _materialize_assets(
    session: Session,
) -> dict[str, EnterpriseAssetModel]:
    assets: dict[str, EnterpriseAssetModel] = {}
    for asset in sorted(SYNTHETIC_ENTERPRISE_ASSETS, key=lambda item: item.asset_key):
        model = _get_or_create(
            session,
            EnterpriseAssetModel,
            EnterpriseAssetModel.asset_key,
            asset.asset_key,
            lambda asset=asset: EnterpriseAssetModel(asset_key=asset.asset_key),
        )
        assert isinstance(model, EnterpriseAssetModel)
        _reconcile_asset(model, asset)
        assets[asset.asset_key] = model
    return assets


def _reconcile_asset(model: EnterpriseAssetModel, asset: EnterpriseAsset) -> None:
    model.asset_type = asset.asset_type.value
    model.name = asset.name
    model.criticality = asset.criticality.value
    model.lifecycle_status = asset.lifecycle_status.value


def _materialize_teams(session: Session) -> dict[str, TeamModel]:
    teams: dict[str, TeamModel] = {}
    for team in sorted(SYNTHETIC_TEAMS, key=lambda item: item.team_key):
        model = _get_or_create(
            session,
            TeamModel,
            TeamModel.team_key,
            team.team_key,
            lambda team=team: TeamModel(team_key=team.team_key),
        )
        assert isinstance(model, TeamModel)
        _reconcile_team(model, team)
        teams[team.team_key] = model
    return teams


def _reconcile_team(model: TeamModel, team: Team) -> None:
    model.name = team.name


def _materialize_ownerships(
    session: Session,
    assets: dict[str, EnterpriseAssetModel],
    teams: dict[str, TeamModel],
) -> None:
    for ownership in sorted(
        SYNTHETIC_ASSET_OWNERSHIPS,
        key=lambda item: (item.asset_key, item.team_key, item.ownership_role.value),
    ):
        asset = assets[ownership.asset_key]
        team = teams[ownership.team_key]
        model = session.scalar(
            select(AssetOwnershipModel).where(
                AssetOwnershipModel.asset_id == asset.id,
                AssetOwnershipModel.team_id == team.id,
                AssetOwnershipModel.ownership_role == ownership.ownership_role.value,
            )
        )
        if model is None:
            session.add(
                AssetOwnershipModel(
                    asset=asset,
                    team=team,
                    ownership_role=ownership.ownership_role.value,
                )
            )


def _materialize_relationships(
    session: Session,
    assets: dict[str, EnterpriseAssetModel],
) -> None:
    for relationship in sorted(
        SYNTHETIC_ASSET_RELATIONSHIPS,
        key=lambda item: (
            item.source_asset_key,
            item.target_asset_key,
            item.relationship_type.value,
        ),
    ):
        source_asset = assets[relationship.source_asset_key]
        target_asset = assets[relationship.target_asset_key]
        model = session.scalar(
            select(AssetRelationshipModel).where(
                AssetRelationshipModel.source_asset_id == source_asset.id,
                AssetRelationshipModel.target_asset_id == target_asset.id,
                AssetRelationshipModel.relationship_type
                == relationship.relationship_type.value,
            )
        )
        if model is None:
            session.add(
                AssetRelationshipModel(
                    source_asset=source_asset,
                    target_asset=target_asset,
                    relationship_type=relationship.relationship_type.value,
                )
            )


def _materialize_incidents(
    session: Session,
    assets: dict[str, EnterpriseAssetModel],
) -> None:
    for incident in sorted(SYNTHETIC_INCIDENTS, key=lambda item: item.incident_key):
        model = _get_or_create(
            session,
            IncidentModel,
            IncidentModel.incident_key,
            incident.incident_key,
            lambda incident=incident: IncidentModel(incident_key=incident.incident_key),
        )
        assert isinstance(model, IncidentModel)
        _reconcile_incident(
            model,
            incident,
            assets[incident.primary_affected_asset_key],
        )


def _reconcile_incident(
    model: IncidentModel,
    incident: Incident,
    primary_affected_asset: EnterpriseAssetModel,
) -> None:
    model.primary_affected_asset = primary_affected_asset
    model.severity = incident.severity.value
    model.title = incident.title
    model.started_at = incident.started_at
    model.resolved_at = incident.resolved_at


def seed_enterprise_estate(session: Session) -> None:
    """Materialize the fictional estate in a caller-owned transaction."""
    assets = _materialize_assets(session)
    teams = _materialize_teams(session)
    session.flush()
    _materialize_ownerships(session, assets, teams)
    _materialize_relationships(session, assets)
    _materialize_incidents(session, assets)
    session.flush()


def main() -> None:
    """Seed the configured database with synthetic PoC enterprise context."""
    from app.core.config import settings
    from app.infrastructure.database.engine import create_database_engine

    engine = create_database_engine(settings)
    try:
        with Session(engine) as session:
            try:
                seed_enterprise_estate(session)
                session.commit()
            except Exception:
                session.rollback()
                raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
