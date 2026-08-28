from dataclasses import fields
from datetime import UTC

from app.domain.enterprise_estate import (
    AssetRelationshipType,
    AssetType,
    EnterpriseAsset,
)
from app.domain.synthetic_enterprise_estate import (
    SYNTHETIC_ASSET_OWNERSHIPS,
    SYNTHETIC_ASSET_RELATIONSHIPS,
    SYNTHETIC_ENTERPRISE_ASSETS,
    SYNTHETIC_INCIDENTS,
    SYNTHETIC_TEAMS,
)


def test_synthetic_enterprise_estate_fixture_is_small_and_deterministic() -> None:
    assert len(SYNTHETIC_ENTERPRISE_ASSETS) == 8
    assert len(SYNTHETIC_TEAMS) == 3
    assert len(SYNTHETIC_ASSET_RELATIONSHIPS) == 8
    assert len(SYNTHETIC_INCIDENTS) == 4
    assert SYNTHETIC_ENTERPRISE_ASSETS == tuple(SYNTHETIC_ENTERPRISE_ASSETS)


def test_synthetic_fixture_has_all_asset_types_and_unique_logical_keys() -> None:
    asset_keys = [asset.asset_key for asset in SYNTHETIC_ENTERPRISE_ASSETS]
    team_keys = [team.team_key for team in SYNTHETIC_TEAMS]
    incident_keys = [incident.incident_key for incident in SYNTHETIC_INCIDENTS]

    assert {asset.asset_type for asset in SYNTHETIC_ENTERPRISE_ASSETS} == set(AssetType)
    assert len(asset_keys) == len(set(asset_keys))
    assert len(team_keys) == len(set(team_keys))
    assert len(incident_keys) == len(set(incident_keys))


def test_synthetic_fixture_references_resolve_to_defined_logical_keys() -> None:
    asset_keys = {asset.asset_key for asset in SYNTHETIC_ENTERPRISE_ASSETS}
    team_keys = {team.team_key for team in SYNTHETIC_TEAMS}

    for ownership in SYNTHETIC_ASSET_OWNERSHIPS:
        assert ownership.asset_key in asset_keys
        assert ownership.team_key in team_keys

    for relationship in SYNTHETIC_ASSET_RELATIONSHIPS:
        assert relationship.source_asset_key in asset_keys
        assert relationship.target_asset_key in asset_keys

    for incident in SYNTHETIC_INCIDENTS:
        assert incident.primary_affected_asset_key in asset_keys


def test_synthetic_fixture_has_shared_service_dependency_topology() -> None:
    dependencies = {
        relationship.source_asset_key: relationship.target_asset_key
        for relationship in SYNTHETIC_ASSET_RELATIONSHIPS
        if relationship.relationship_type is AssetRelationshipType.DEPENDS_ON
    }

    assert dependencies == {
        "svc-asteria-editor": "svc-orbit-catalog",
        "svc-borealis-renderer": "svc-orbit-catalog",
    }


def test_synthetic_fixture_has_recurring_timezone_aware_incident_context() -> None:
    orbit_incidents = [
        incident
        for incident in SYNTHETIC_INCIDENTS
        if incident.primary_affected_asset_key == "svc-orbit-catalog"
    ]

    assert len(orbit_incidents) == 3
    assert len({incident.started_at for incident in orbit_incidents}) == 3
    for incident in SYNTHETIC_INCIDENTS:
        assert incident.started_at.tzinfo is UTC
        assert incident.resolved_at is not None
        assert incident.resolved_at.tzinfo is UTC


def test_synthetic_fixture_introduces_no_risk_or_technical_debt_concepts() -> None:
    assert "risk" not in {field.name for field in fields(EnterpriseAsset)}
    assert "TechnicalDebt" not in str(SYNTHETIC_ENTERPRISE_ASSETS)
