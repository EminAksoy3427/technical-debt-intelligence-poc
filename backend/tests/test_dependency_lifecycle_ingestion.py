import importlib
import inspect
from dataclasses import fields
from pathlib import Path

import pytest

from app.dependency_lifecycle_ingestion import (
    DEPENDENCY_EOL_SIGNAL_TYPE,
    DEPENDENCY_LIFECYCLE_SOURCE_SYSTEM,
    normalize_dependency_lifecycle_finding,
)
from app.domain.assets import CanonicalAssetRef
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Evidence, Signal, SourceObservationRef
from app.infrastructure.dependency_lifecycle import load_dependency_lifecycle_findings
from app.signal_ingestion import NormalizedSignal

SOURCE_PATH = (
    Path(__file__).resolve().parents[2]
    / "synthetic_sources"
    / "dependency_lifecycle_findings.json"
)


def _finding():
    return load_dependency_lifecycle_findings(SOURCE_PATH)[0]


def _affected_asset() -> CanonicalAssetRef:
    return CanonicalAssetRef(
        asset_key="repo-borealis-renderer",
        asset_type=AssetType.REPOSITORY,
    )


def _normalize() -> NormalizedSignal:
    return normalize_dependency_lifecycle_finding(
        _finding(),
        affected_asset=_affected_asset(),
    )


def test_lifecycle_finding_normalizes_to_the_approved_canonical_signal() -> None:
    finding = _finding()
    normalized = _normalize()

    assert normalized.signal.source_system == DEPENDENCY_LIFECYCLE_SOURCE_SYSTEM
    assert normalized.signal.signal_type == DEPENDENCY_EOL_SIGNAL_TYPE
    assert normalized.provenance == SourceObservationRef(
        source_system="dependency-lifecycle",
        source_record_id=finding.source_record_id,
    )
    assert normalized.signal.source_record_id == finding.source_record_id


def test_same_lifecycle_finding_has_deterministic_ids() -> None:
    first = _normalize()
    repeated = _normalize()

    assert repeated.provenance == first.provenance
    assert repeated.signal.signal_id == first.signal.signal_id
    assert repeated.evidence == first.evidence
    assert repeated == first


def test_lifecycle_observation_timestamp_is_distinct_from_eol_date() -> None:
    finding = _finding()
    normalized = _normalize()
    evidence = next(iter(normalized.evidence))

    assert normalized.signal.detected_at == finding.observed_at
    assert normalized.signal.detected_at.utcoffset() is not None
    assert evidence.captured_at == finding.observed_at
    assert normalized.signal.detected_at.date() != finding.eol_date


def test_lifecycle_normalization_preserves_asset_and_concise_provenance() -> None:
    finding = _finding()
    normalized = _normalize()
    evidence = next(iter(normalized.evidence))

    assert normalized.signal.affected_asset == _affected_asset()
    assert normalized.signal.severity is None
    assert finding.source_record_id in evidence.source_reference
    assert finding.affected_asset_key in evidence.source_reference
    assert finding.component_name in evidence.source_reference
    assert finding.component_version in evidence.source_reference
    assert finding.lifecycle_status.value in evidence.source_reference
    assert finding.eol_date.isoformat() in evidence.source_reference
    assert evidence.reference_uri is None
    assert "risk" not in {field.name for field in fields(Signal)}


def test_lifecycle_finding_does_not_leak_into_canonical_contract() -> None:
    signal_fields = {field.name for field in fields(Signal)}
    normalized_fields = {field.name for field in fields(NormalizedSignal)}
    evidence_fields = {field.name for field in fields(Evidence)}

    assert {
        "component_name",
        "component_version",
        "lifecycle_status",
        "eol_date",
    }.isdisjoint(signal_fields)
    assert normalized_fields == {"signal", "evidence"}
    assert {"validated", "validation_status", "validated_by"}.isdisjoint(
        evidence_fields
    )


def test_lifecycle_ingestion_has_no_correlation_or_ground_truth_contract() -> None:
    ingestion_source = inspect.getsource(
        importlib.import_module("app.dependency_lifecycle_ingestion")
    ).lower()
    source_boundary = inspect.getsource(
        importlib.import_module("app.infrastructure.dependency_lifecycle")
    ).lower()

    assert "candidate" not in ingestion_source
    assert "candidate" not in source_boundary
    assert "ground_truth" not in ingestion_source
    assert "ground_truth" not in source_boundary
    assert "datetime.now" not in ingestion_source
    assert "datetime.now" not in source_boundary


def test_lifecycle_normalization_rejects_a_non_matching_affected_asset() -> None:
    with pytest.raises(ValueError, match="must match"):
        normalize_dependency_lifecycle_finding(
            _finding(),
            affected_asset=CanonicalAssetRef(
                asset_key="repo-orbit-catalog",
                asset_type=AssetType.REPOSITORY,
            ),
        )
