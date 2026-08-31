from dataclasses import dataclass
from uuid import UUID

from app.domain.enterprise_estate import (
    AssetOwnership,
    AssetRelationship,
    EnterpriseAsset,
    Incident,
    Team,
)


@dataclass(frozen=True)
class EnterpriseAssetOwnership:
    asset_ownership: AssetOwnership
    team: Team

    def __post_init__(self) -> None:
        if self.asset_ownership.team_key != self.team.team_key:
            raise ValueError("Enterprise ownership team identity must match")


@dataclass(frozen=True)
class CandidateEnterpriseContext:
    candidate_id: UUID
    enterprise_asset: EnterpriseAsset
    enterprise_ownerships: tuple[EnterpriseAssetOwnership, ...]
    direct_relationships: tuple[AssetRelationship, ...]
    direct_incidents: tuple[Incident, ...]

    def __post_init__(self) -> None:
        ownerships = tuple(self.enterprise_ownerships)
        relationships = tuple(self.direct_relationships)
        incidents = tuple(self.direct_incidents)
        asset_key = self.enterprise_asset.asset_key

        if any(
            ownership.asset_ownership.asset_key != asset_key for ownership in ownerships
        ):
            raise ValueError("Enterprise ownership must reference the context asset")
        if any(
            relationship.source_asset_key != asset_key
            and relationship.target_asset_key != asset_key
            for relationship in relationships
        ):
            raise ValueError("Direct relationship must touch the context asset")
        if any(
            incident.primary_affected_asset_key != asset_key for incident in incidents
        ):
            raise ValueError("Direct incident must reference the context asset")

        object.__setattr__(self, "enterprise_ownerships", ownerships)
        object.__setattr__(self, "direct_relationships", relationships)
        object.__setattr__(self, "direct_incidents", incidents)
