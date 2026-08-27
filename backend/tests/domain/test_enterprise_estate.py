from collections.abc import Callable
from dataclasses import fields
from datetime import UTC, datetime

import pytest

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


@pytest.mark.parametrize("asset_type", list(AssetType))
def test_supported_enterprise_asset_types_are_canonical(
    asset_type: AssetType,
) -> None:
    asset = EnterpriseAsset(
        asset_key=f"asset-{asset_type.value.lower()}",
        asset_type=asset_type,
        name=f"Synthetic {asset_type.value.title()}",
        criticality=AssetCriticality.HIGH,
        lifecycle_status=AssetLifecycleStatus.ACTIVE,
    )

    assert asset.asset_type is asset_type


@pytest.mark.parametrize(
    ("factory", "match"),
    [
        (
            lambda: EnterpriseAsset(
                asset_key=" ",
                asset_type=AssetType.APPLICATION,
                name="Synthetic Application",
                criticality=AssetCriticality.HIGH,
                lifecycle_status=AssetLifecycleStatus.ACTIVE,
            ),
            "asset key",
        ),
        (lambda: Team(team_key="\t", name="Synthetic Team"), "Team key"),
        (
            lambda: Incident(
                incident_key="",
                primary_affected_asset_key="asset-service",
                severity=IncidentSeverity.MEDIUM,
                title="Synthetic service interruption",
                started_at=datetime(2026, 1, 15, 9, 0, tzinfo=UTC),
            ),
            "Incident key",
        ),
    ],
)
def test_stable_logical_keys_must_not_be_blank(
    factory: Callable[[], object],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        factory()


def test_asset_criticality_is_context_without_a_risk_field() -> None:
    asset = EnterpriseAsset(
        asset_key="asset-application",
        asset_type=AssetType.APPLICATION,
        name="Synthetic Application",
        criticality=AssetCriticality.CRITICAL,
        lifecycle_status=AssetLifecycleStatus.ACTIVE,
    )

    assert asset.criticality is AssetCriticality.CRITICAL
    assert "risk" not in {field.name for field in fields(EnterpriseAsset)}


def test_asset_ownership_links_an_asset_key_to_a_team_key() -> None:
    ownership = AssetOwnership(
        asset_key="asset-service",
        team_key="team-platform",
        ownership_role=OwnershipRole.PRIMARY,
    )

    assert ownership.asset_key == "asset-service"
    assert ownership.team_key == "team-platform"
    assert ownership.ownership_role is OwnershipRole.PRIMARY


def test_asset_relationship_preserves_direction() -> None:
    relationship = AssetRelationship(
        source_asset_key="asset-application",
        target_asset_key="asset-service",
        relationship_type=AssetRelationshipType.DEPENDS_ON,
    )

    assert relationship.source_asset_key == "asset-application"
    assert relationship.target_asset_key == "asset-service"
    assert relationship.relationship_type is AssetRelationshipType.DEPENDS_ON


def test_incident_references_a_canonical_asset_key() -> None:
    incident = Incident(
        incident_key="incident-001",
        primary_affected_asset_key="asset-service",
        severity=IncidentSeverity.HIGH,
        title="Synthetic service interruption",
        started_at=datetime(2026, 1, 15, 9, 0, tzinfo=UTC),
        resolved_at=datetime(2026, 1, 15, 9, 30, tzinfo=UTC),
    )

    assert incident.primary_affected_asset_key == "asset-service"
    assert incident.resolved_at is not None


def test_incident_rejects_resolution_before_start() -> None:
    with pytest.raises(ValueError, match="must not precede"):
        Incident(
            incident_key="incident-001",
            primary_affected_asset_key="asset-service",
            severity=IncidentSeverity.HIGH,
            title="Synthetic service interruption",
            started_at=datetime(2026, 1, 15, 9, 0, tzinfo=UTC),
            resolved_at=datetime(2026, 1, 15, 8, 59, tzinfo=UTC),
        )
