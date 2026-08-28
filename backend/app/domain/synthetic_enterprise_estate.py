from datetime import UTC, datetime

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

SYNTHETIC_ENTERPRISE_ASSETS = (
    EnterpriseAsset(
        asset_key="app-asteria-canvas",
        asset_type=AssetType.APPLICATION,
        name="Asteria Canvas Application",
        criticality=AssetCriticality.HIGH,
        lifecycle_status=AssetLifecycleStatus.ACTIVE,
    ),
    EnterpriseAsset(
        asset_key="app-borealis-workshop",
        asset_type=AssetType.APPLICATION,
        name="Borealis Workshop Application",
        criticality=AssetCriticality.HIGH,
        lifecycle_status=AssetLifecycleStatus.ACTIVE,
    ),
    EnterpriseAsset(
        asset_key="repo-asteria-editor",
        asset_type=AssetType.REPOSITORY,
        name="Asteria Editor Repository",
        criticality=AssetCriticality.MEDIUM,
        lifecycle_status=AssetLifecycleStatus.ACTIVE,
    ),
    EnterpriseAsset(
        asset_key="repo-borealis-renderer",
        asset_type=AssetType.REPOSITORY,
        name="Borealis Renderer Repository",
        criticality=AssetCriticality.MEDIUM,
        lifecycle_status=AssetLifecycleStatus.ACTIVE,
    ),
    EnterpriseAsset(
        asset_key="repo-orbit-catalog",
        asset_type=AssetType.REPOSITORY,
        name="Orbit Catalog Repository",
        criticality=AssetCriticality.MEDIUM,
        lifecycle_status=AssetLifecycleStatus.ACTIVE,
    ),
    EnterpriseAsset(
        asset_key="svc-asteria-editor",
        asset_type=AssetType.SERVICE,
        name="Asteria Editor Service",
        criticality=AssetCriticality.HIGH,
        lifecycle_status=AssetLifecycleStatus.ACTIVE,
    ),
    EnterpriseAsset(
        asset_key="svc-borealis-renderer",
        asset_type=AssetType.SERVICE,
        name="Borealis Renderer Service",
        criticality=AssetCriticality.HIGH,
        lifecycle_status=AssetLifecycleStatus.ACTIVE,
    ),
    EnterpriseAsset(
        asset_key="svc-orbit-catalog",
        asset_type=AssetType.SERVICE,
        name="Orbit Catalog Service",
        criticality=AssetCriticality.HIGH,
        lifecycle_status=AssetLifecycleStatus.ACTIVE,
    ),
)

SYNTHETIC_TEAMS = (
    Team(team_key="team-asteria", name="Asteria Studio Team"),
    Team(team_key="team-borealis", name="Borealis Studio Team"),
    Team(team_key="team-orbit", name="Orbit Platform Team"),
)

SYNTHETIC_ASSET_OWNERSHIPS = (
    AssetOwnership("app-asteria-canvas", "team-asteria", OwnershipRole.PRIMARY),
    AssetOwnership("app-asteria-canvas", "team-orbit", OwnershipRole.SUPPORTING),
    AssetOwnership("app-borealis-workshop", "team-borealis", OwnershipRole.PRIMARY),
    AssetOwnership("repo-asteria-editor", "team-asteria", OwnershipRole.PRIMARY),
    AssetOwnership("repo-borealis-renderer", "team-borealis", OwnershipRole.PRIMARY),
    AssetOwnership("repo-orbit-catalog", "team-orbit", OwnershipRole.PRIMARY),
    AssetOwnership("svc-asteria-editor", "team-asteria", OwnershipRole.PRIMARY),
    AssetOwnership("svc-borealis-renderer", "team-borealis", OwnershipRole.PRIMARY),
    AssetOwnership("svc-orbit-catalog", "team-orbit", OwnershipRole.PRIMARY),
)

SYNTHETIC_ASSET_RELATIONSHIPS = (
    AssetRelationship(
        "app-asteria-canvas",
        "svc-asteria-editor",
        AssetRelationshipType.CONTAINS,
    ),
    AssetRelationship(
        "app-asteria-canvas",
        "svc-orbit-catalog",
        AssetRelationshipType.CONTAINS,
    ),
    AssetRelationship(
        "app-borealis-workshop",
        "svc-borealis-renderer",
        AssetRelationshipType.CONTAINS,
    ),
    AssetRelationship(
        "svc-asteria-editor",
        "repo-asteria-editor",
        AssetRelationshipType.IMPLEMENTED_BY,
    ),
    AssetRelationship(
        "svc-borealis-renderer",
        "repo-borealis-renderer",
        AssetRelationshipType.IMPLEMENTED_BY,
    ),
    AssetRelationship(
        "svc-orbit-catalog",
        "repo-orbit-catalog",
        AssetRelationshipType.IMPLEMENTED_BY,
    ),
    AssetRelationship(
        "svc-asteria-editor",
        "svc-orbit-catalog",
        AssetRelationshipType.DEPENDS_ON,
    ),
    AssetRelationship(
        "svc-borealis-renderer",
        "svc-orbit-catalog",
        AssetRelationshipType.DEPENDS_ON,
    ),
)

SYNTHETIC_INCIDENTS = (
    Incident(
        incident_key="inc-orbit-001",
        primary_affected_asset_key="svc-orbit-catalog",
        severity=IncidentSeverity.MEDIUM,
        title="Orbit catalog refresh delay",
        started_at=datetime(2026, 1, 12, 9, 0, tzinfo=UTC),
        resolved_at=datetime(2026, 1, 12, 9, 22, tzinfo=UTC),
    ),
    Incident(
        incident_key="inc-orbit-002",
        primary_affected_asset_key="svc-orbit-catalog",
        severity=IncidentSeverity.HIGH,
        title="Orbit catalog query interruption",
        started_at=datetime(2026, 2, 3, 14, 10, tzinfo=UTC),
        resolved_at=datetime(2026, 2, 3, 14, 47, tzinfo=UTC),
    ),
    Incident(
        incident_key="inc-orbit-003",
        primary_affected_asset_key="svc-orbit-catalog",
        severity=IncidentSeverity.MEDIUM,
        title="Orbit catalog indexing delay",
        started_at=datetime(2026, 3, 8, 11, 30, tzinfo=UTC),
        resolved_at=datetime(2026, 3, 8, 12, 5, tzinfo=UTC),
    ),
    Incident(
        incident_key="inc-asteria-001",
        primary_affected_asset_key="svc-asteria-editor",
        severity=IncidentSeverity.LOW,
        title="Asteria editor preview delay",
        started_at=datetime(2026, 4, 16, 16, 0, tzinfo=UTC),
        resolved_at=datetime(2026, 4, 16, 16, 18, tzinfo=UTC),
    ),
)
