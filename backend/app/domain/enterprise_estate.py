from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AssetType(StrEnum):
    APPLICATION = "APPLICATION"
    SERVICE = "SERVICE"
    REPOSITORY = "REPOSITORY"


class AssetCriticality(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AssetLifecycleStatus(StrEnum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class OwnershipRole(StrEnum):
    PRIMARY = "PRIMARY"
    SUPPORTING = "SUPPORTING"


class AssetRelationshipType(StrEnum):
    CONTAINS = "CONTAINS"
    IMPLEMENTED_BY = "IMPLEMENTED_BY"
    DEPENDS_ON = "DEPENDS_ON"


class IncidentSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


def _require_non_blank(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")


@dataclass(frozen=True)
class EnterpriseAsset:
    asset_key: str
    asset_type: AssetType
    name: str
    criticality: AssetCriticality
    lifecycle_status: AssetLifecycleStatus

    def __post_init__(self) -> None:
        _require_non_blank(self.asset_key, "Enterprise asset key")
        _require_non_blank(self.name, "Enterprise asset name")
        if not isinstance(self.asset_type, AssetType):
            raise ValueError("Enterprise asset type must be supported")
        if not isinstance(self.criticality, AssetCriticality):
            raise ValueError("Enterprise asset criticality must be supported")
        if not isinstance(self.lifecycle_status, AssetLifecycleStatus):
            raise ValueError("Enterprise asset lifecycle status must be supported")


@dataclass(frozen=True)
class Team:
    team_key: str
    name: str

    def __post_init__(self) -> None:
        _require_non_blank(self.team_key, "Team key")
        _require_non_blank(self.name, "Team name")


@dataclass(frozen=True)
class AssetOwnership:
    asset_key: str
    team_key: str
    ownership_role: OwnershipRole

    def __post_init__(self) -> None:
        _require_non_blank(self.asset_key, "Asset ownership asset key")
        _require_non_blank(self.team_key, "Asset ownership team key")
        if not isinstance(self.ownership_role, OwnershipRole):
            raise ValueError("Asset ownership role must be supported")


@dataclass(frozen=True)
class AssetRelationship:
    source_asset_key: str
    target_asset_key: str
    relationship_type: AssetRelationshipType

    def __post_init__(self) -> None:
        _require_non_blank(self.source_asset_key, "Relationship source asset key")
        _require_non_blank(self.target_asset_key, "Relationship target asset key")
        if not isinstance(self.relationship_type, AssetRelationshipType):
            raise ValueError("Asset relationship type must be supported")


@dataclass(frozen=True)
class Incident:
    incident_key: str
    primary_affected_asset_key: str
    severity: IncidentSeverity
    title: str
    started_at: datetime
    resolved_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_non_blank(self.incident_key, "Incident key")
        _require_non_blank(
            self.primary_affected_asset_key,
            "Incident primary affected asset key",
        )
        _require_non_blank(self.title, "Incident title")
        if not isinstance(self.severity, IncidentSeverity):
            raise ValueError("Incident severity must be supported")
        if self.started_at.tzinfo is None or self.started_at.utcoffset() is None:
            raise ValueError("Incident start timestamp must be timezone-aware")
        if self.resolved_at is not None:
            if self.resolved_at.tzinfo is None or self.resolved_at.utcoffset() is None:
                raise ValueError("Incident resolution timestamp must be timezone-aware")
            if self.resolved_at < self.started_at:
                raise ValueError(
                    "Incident resolution timestamp must not precede start timestamp"
                )
