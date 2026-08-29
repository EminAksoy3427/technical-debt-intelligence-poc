import importlib
import inspect
from dataclasses import fields

import pytest

from app.domain.assets import CanonicalAssetRef
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Evidence, Signal, SourceObservationRef
from app.domain.synthetic_enterprise_estate import (
    SYNTHETIC_ENTERPRISE_ASSETS,
    SYNTHETIC_INCIDENTS,
)
from app.incident_ingestion import (
    INCIDENT_SIGNAL_TYPE,
    INCIDENT_SOURCE_SYSTEM,
    normalize_incident,
)
from app.signal_ingestion import NormalizedSignal

_ASSET_TYPES_BY_KEY = {
    asset.asset_key: asset.asset_type for asset in SYNTHETIC_ENTERPRISE_ASSETS
}


def _affected_asset(incident_key: str) -> CanonicalAssetRef:
    incident = next(
        item for item in SYNTHETIC_INCIDENTS if item.incident_key == incident_key
    )
    return CanonicalAssetRef(
        asset_key=incident.primary_affected_asset_key,
        asset_type=_ASSET_TYPES_BY_KEY[incident.primary_affected_asset_key],
    )


def _normalize(incident_key: str) -> NormalizedSignal:
    incident = next(
        item for item in SYNTHETIC_INCIDENTS if item.incident_key == incident_key
    )
    return normalize_incident(
        incident,
        primary_affected_asset=_affected_asset(incident_key),
    )


def test_incident_normalizes_to_the_approved_canonical_signal() -> None:
    incident = next(
        item for item in SYNTHETIC_INCIDENTS if item.incident_key == "inc-orbit-001"
    )
    normalized = _normalize(incident.incident_key)

    assert normalized.signal.source_system == INCIDENT_SOURCE_SYSTEM
    assert normalized.signal.signal_type == INCIDENT_SIGNAL_TYPE
    assert normalized.provenance == SourceObservationRef(
        source_system="incident-management",
        source_record_id="inc-orbit-001",
    )
    assert normalized.signal.source_record_id == incident.incident_key


def test_same_incident_has_deterministic_provenance_signal_and_evidence_ids() -> None:
    first = _normalize("inc-orbit-001")
    repeated = _normalize("inc-orbit-001")

    assert repeated.provenance == first.provenance
    assert repeated.signal.signal_id == first.signal.signal_id
    assert repeated.evidence == first.evidence
    assert repeated == first


def test_incident_normalization_preserves_source_timestamp_asset_and_severity() -> None:
    incident = next(
        item for item in SYNTHETIC_INCIDENTS if item.incident_key == "inc-orbit-002"
    )
    normalized = _normalize(incident.incident_key)
    evidence = next(iter(normalized.evidence))

    assert normalized.signal.detected_at == incident.started_at
    assert normalized.signal.detected_at.utcoffset() is not None
    assert evidence.captured_at == incident.started_at
    assert normalized.signal.affected_asset == CanonicalAssetRef(
        asset_key="svc-orbit-catalog",
        asset_type=AssetType.SERVICE,
    )
    assert normalized.signal.severity == incident.severity.value
    assert "risk" not in {field.name for field in fields(Signal)}
    assert evidence.source_reference.startswith(f"{incident.incident_key}:")
    assert incident.title in evidence.source_reference
    assert "svc-orbit-catalog" in evidence.source_reference
    assert evidence.reference_uri is None


def test_orbit_incidents_remain_distinct_operational_incident_signals() -> None:
    orbit_keys = ("inc-orbit-001", "inc-orbit-002", "inc-orbit-003")
    normalized = tuple(_normalize(incident_key) for incident_key in orbit_keys)

    assert {item.signal.source_record_id for item in normalized} == set(orbit_keys)
    assert len({item.signal.signal_id for item in normalized}) == 3
    assert {item.signal.signal_type for item in normalized} == {
        "OPERATIONAL_INCIDENT"
    }
    assert "RECURRING_INCIDENT_PATTERN" not in {
        item.signal.signal_type for item in normalized
    }


def test_incident_ingestion_has_no_validation_or_correlation_contract() -> None:
    ingestion_source = inspect.getsource(
        importlib.import_module("app.incident_ingestion")
    ).lower()
    normalized_fields = {field.name for field in fields(NormalizedSignal)}
    evidence_fields = {field.name for field in fields(Evidence)}

    assert normalized_fields == {"signal", "evidence"}
    assert {"validated", "validation_status", "validated_by"}.isdisjoint(
        evidence_fields
    )
    assert "candidate" not in ingestion_source
    assert "ground_truth" not in ingestion_source
    assert "datetime.now" not in ingestion_source


def test_incident_normalization_rejects_a_non_matching_primary_asset() -> None:
    incident = next(
        item for item in SYNTHETIC_INCIDENTS if item.incident_key == "inc-orbit-001"
    )

    with pytest.raises(ValueError, match="must match"):
        normalize_incident(
            incident,
            primary_affected_asset=CanonicalAssetRef(
                asset_key="svc-asteria-editor",
                asset_type=AssetType.SERVICE,
            ),
        )
