from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased

from app.domain.candidate_enterprise_context import (
    CandidateEnterpriseContext,
    EnterpriseAssetOwnership,
)
from app.domain.enterprise_estate import (
    AssetCriticality,
    AssetLifecycleStatus,
    AssetOwnership,
    AssetRelationship,
    AssetRelationshipType,
    AssetType,
    EnterpriseAsset,
    Incident,
    IncidentSeverity,
    OwnershipRole,
    Team,
)
from app.infrastructure.database.candidate_models import CandidateModel
from app.infrastructure.database.enterprise_estate_models import (
    AssetOwnershipModel,
    AssetRelationshipModel,
    EnterpriseAssetModel,
    IncidentModel,
    TeamModel,
)


class CandidateEnterpriseContextIntegrityError(ValueError):
    """A persisted Candidate cannot be projected from enterprise estate facts."""


def load_candidate_enterprise_context(
    session: Session,
    candidate_id: UUID,
) -> CandidateEnterpriseContext | None:
    """Load factual enterprise context for a persisted Candidate's asset."""
    with session.no_autoflush:
        candidate_row = session.execute(
            select(
                CandidateModel.candidate_id,
                CandidateModel.canonical_asset_id,
            ).where(CandidateModel.candidate_id == candidate_id)
        ).one_or_none()
        if candidate_row is None:
            return None
        if candidate_row.canonical_asset_id is None:
            raise CandidateEnterpriseContextIntegrityError(
                "Candidate canonical enterprise asset identity is missing"
            )
        canonical_asset_id = candidate_row.canonical_asset_id

        enterprise_asset = _load_enterprise_asset(session, canonical_asset_id)
        enterprise_ownerships = _load_enterprise_ownerships(
            session,
            canonical_asset_id,
            enterprise_asset.asset_key,
        )
        direct_relationships = _load_direct_relationships(
            session,
            canonical_asset_id,
        )
        direct_incidents = _load_direct_incidents(
            session,
            canonical_asset_id,
            enterprise_asset.asset_key,
        )

    return CandidateEnterpriseContext(
        candidate_id=candidate_id,
        enterprise_asset=enterprise_asset,
        enterprise_ownerships=enterprise_ownerships,
        direct_relationships=direct_relationships,
        direct_incidents=direct_incidents,
    )


def _load_enterprise_asset(
    session: Session,
    canonical_asset_id: int,
) -> EnterpriseAsset:
    row = session.execute(
        select(
            EnterpriseAssetModel.asset_key,
            EnterpriseAssetModel.asset_type,
            EnterpriseAssetModel.name,
            EnterpriseAssetModel.criticality,
            EnterpriseAssetModel.lifecycle_status,
        ).where(EnterpriseAssetModel.id == canonical_asset_id)
    ).one_or_none()
    if row is None:
        raise CandidateEnterpriseContextIntegrityError(
            "Candidate canonical enterprise asset is missing"
        )

    try:
        return EnterpriseAsset(
            asset_key=row.asset_key,
            asset_type=AssetType(row.asset_type),
            name=row.name,
            criticality=AssetCriticality(row.criticality),
            lifecycle_status=AssetLifecycleStatus(row.lifecycle_status),
        )
    except ValueError as error:
        raise CandidateEnterpriseContextIntegrityError(
            "Candidate canonical enterprise asset is invalid"
        ) from error


def _load_enterprise_ownerships(
    session: Session,
    canonical_asset_id: int,
    asset_key: str,
) -> tuple[EnterpriseAssetOwnership, ...]:
    rows = session.execute(
        select(
            AssetOwnershipModel.ownership_role,
            TeamModel.team_key,
            TeamModel.name,
        )
        .select_from(AssetOwnershipModel)
        .outerjoin(TeamModel, TeamModel.id == AssetOwnershipModel.team_id)
        .where(AssetOwnershipModel.asset_id == canonical_asset_id)
    )
    ownerships: list[EnterpriseAssetOwnership] = []
    for row in rows:
        if row.team_key is None or row.name is None:
            raise CandidateEnterpriseContextIntegrityError(
                "Candidate enterprise ownership Team is missing"
            )
        try:
            ownerships.append(
                EnterpriseAssetOwnership(
                    asset_ownership=AssetOwnership(
                        asset_key=asset_key,
                        team_key=row.team_key,
                        ownership_role=OwnershipRole(row.ownership_role),
                    ),
                    team=Team(team_key=row.team_key, name=row.name),
                )
            )
        except ValueError as error:
            raise CandidateEnterpriseContextIntegrityError(
                "Candidate enterprise ownership is invalid"
            ) from error

    return tuple(
        sorted(
            ownerships,
            key=lambda item: (
                item.asset_ownership.ownership_role.value,
                item.team.team_key,
            ),
        )
    )


def _load_direct_relationships(
    session: Session,
    canonical_asset_id: int,
) -> tuple[AssetRelationship, ...]:
    source_asset = aliased(EnterpriseAssetModel)
    target_asset = aliased(EnterpriseAssetModel)
    rows = session.execute(
        select(
            AssetRelationshipModel.relationship_type,
            source_asset.asset_key.label("source_asset_key"),
            target_asset.asset_key.label("target_asset_key"),
        )
        .select_from(AssetRelationshipModel)
        .outerjoin(
            source_asset,
            source_asset.id == AssetRelationshipModel.source_asset_id,
        )
        .outerjoin(
            target_asset,
            target_asset.id == AssetRelationshipModel.target_asset_id,
        )
        .where(
            or_(
                AssetRelationshipModel.source_asset_id == canonical_asset_id,
                AssetRelationshipModel.target_asset_id == canonical_asset_id,
            )
        )
    )
    relationships: list[AssetRelationship] = []
    for row in rows:
        if row.source_asset_key is None or row.target_asset_key is None:
            raise CandidateEnterpriseContextIntegrityError(
                "Candidate direct enterprise relationship asset is missing"
            )
        try:
            relationships.append(
                AssetRelationship(
                    source_asset_key=row.source_asset_key,
                    target_asset_key=row.target_asset_key,
                    relationship_type=AssetRelationshipType(row.relationship_type),
                )
            )
        except ValueError as error:
            raise CandidateEnterpriseContextIntegrityError(
                "Candidate direct enterprise relationship is invalid"
            ) from error

    return tuple(
        sorted(
            relationships,
            key=lambda item: (
                item.relationship_type.value,
                item.source_asset_key,
                item.target_asset_key,
            ),
        )
    )


def _load_direct_incidents(
    session: Session,
    canonical_asset_id: int,
    asset_key: str,
) -> tuple[Incident, ...]:
    rows = session.execute(
        select(
            IncidentModel.incident_key,
            IncidentModel.severity,
            IncidentModel.title,
            IncidentModel.started_at,
            IncidentModel.resolved_at,
        ).where(IncidentModel.primary_affected_asset_id == canonical_asset_id)
    )
    incidents: list[Incident] = []
    for row in rows:
        try:
            incidents.append(
                Incident(
                    incident_key=row.incident_key,
                    primary_affected_asset_key=asset_key,
                    severity=IncidentSeverity(row.severity),
                    title=row.title,
                    started_at=row.started_at,
                    resolved_at=row.resolved_at,
                )
            )
        except ValueError as error:
            raise CandidateEnterpriseContextIntegrityError(
                "Candidate direct enterprise incident is invalid"
            ) from error

    return tuple(
        sorted(
            incidents,
            key=lambda item: (item.started_at, item.incident_key),
        )
    )
