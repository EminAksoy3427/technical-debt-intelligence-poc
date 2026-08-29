from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.domain.assets import CanonicalAssetRef
from app.domain.enterprise_estate import AssetType, Incident, IncidentSeverity
from app.infrastructure.database.enterprise_estate_models import IncidentModel


def load_incidents_with_affected_assets(
    session: Session,
    *,
    incident_keys: tuple[str, ...] | None = None,
) -> tuple[tuple[Incident, CanonicalAssetRef], ...]:
    """Load runtime Incident facts and their primary affected asset references."""
    query = (
        select(IncidentModel)
        .options(joinedload(IncidentModel.primary_affected_asset))
        .order_by(IncidentModel.incident_key)
    )
    if incident_keys is not None:
        query = query.where(IncidentModel.incident_key.in_(incident_keys))

    incident_models = session.scalars(query)
    return tuple(
        _to_domain_incident_with_affected_asset(incident_model)
        for incident_model in incident_models
    )


def _to_domain_incident_with_affected_asset(
    incident_model: IncidentModel,
) -> tuple[Incident, CanonicalAssetRef]:
    affected_asset = incident_model.primary_affected_asset
    if affected_asset is None:
        raise ValueError("Incident primary affected asset is missing")

    incident = Incident(
        incident_key=incident_model.incident_key,
        primary_affected_asset_key=affected_asset.asset_key,
        severity=IncidentSeverity(incident_model.severity),
        title=incident_model.title,
        started_at=incident_model.started_at,
        resolved_at=incident_model.resolved_at,
    )
    return incident, CanonicalAssetRef(
        asset_key=affected_asset.asset_key,
        asset_type=AssetType(affected_asset.asset_type),
    )
