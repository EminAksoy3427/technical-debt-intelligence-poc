from dataclasses import fields
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.domain.assets import CanonicalAssetRef
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Evidence, Signal, SourceObservationRef
from app.signal_ingestion import NormalizedSignal


def _normalized_signal(
    *,
    signal_id: str,
    evidence_id: str,
    source_system: str,
    source_record_id: str,
    detected_at: datetime,
    signal_type: str,
    asset_key: str,
    asset_type: AssetType,
    severity: str | None,
    source_reference: str,
) -> NormalizedSignal:
    evidence_uuid = UUID(evidence_id)
    evidence = Evidence(
        evidence_id=evidence_uuid,
        source_system=source_system,
        source_reference=source_reference,
        captured_at=detected_at,
    )
    signal = Signal(
        signal_id=UUID(signal_id),
        source_system=source_system,
        source_record_id=source_record_id,
        detected_at=detected_at,
        signal_type=signal_type,
        affected_asset=CanonicalAssetRef(
            asset_key=asset_key,
            asset_type=asset_type,
        ),
        severity=severity,
        evidence_ids=frozenset({evidence_uuid}),
    )
    return NormalizedSignal(signal=signal, evidence=frozenset({evidence}))


def test_contract_represents_semgrep_signal_without_incident_fields() -> None:
    normalized = _normalized_signal(
        signal_id="00000000-0000-0000-0000-000000000101",
        evidence_id="00000000-0000-0000-0000-000000000201",
        source_system="semgrep",
        source_record_id=(
            "repo-borealis-renderer:renderer_client.py:"
            "python.requests.missing-timeout:6"
        ),
        detected_at=datetime(2026, 8, 28, 9, 0, tzinfo=UTC),
        signal_type="MISSING_TIMEOUT",
        asset_key="repo-borealis-renderer",
        asset_type=AssetType.REPOSITORY,
        severity="MEDIUM",
        source_reference="renderer_client.py:6:python.requests.missing-timeout",
    )

    assert normalized.signal.affected_asset == CanonicalAssetRef(
        asset_key="repo-borealis-renderer",
        asset_type=AssetType.REPOSITORY,
    )
    assert normalized.signal.source_system == "semgrep"
    assert normalized.signal.signal_type == "MISSING_TIMEOUT"
    assert normalized.provenance == SourceObservationRef(
        source_system="semgrep",
        source_record_id=(
            "repo-borealis-renderer:renderer_client.py:"
            "python.requests.missing-timeout:6"
        ),
    )
    assert "incident_key" not in {field.name for field in fields(Signal)}


def test_contract_represents_incident_signal_without_scanner_fields() -> None:
    normalized = _normalized_signal(
        signal_id="00000000-0000-0000-0000-000000000102",
        evidence_id="00000000-0000-0000-0000-000000000202",
        source_system="incident-management",
        source_record_id="inc-orbit-001",
        detected_at=datetime(2026, 1, 12, 9, 0, tzinfo=UTC),
        signal_type="OPERATIONAL_INCIDENT",
        asset_key="svc-orbit-catalog",
        asset_type=AssetType.SERVICE,
        severity="MEDIUM",
        source_reference="inc-orbit-001",
    )

    assert normalized.signal.affected_asset == CanonicalAssetRef(
        asset_key="svc-orbit-catalog",
        asset_type=AssetType.SERVICE,
    )
    assert normalized.signal.source_system == "incident-management"
    assert normalized.signal.signal_type == "OPERATIONAL_INCIDENT"
    assert normalized.provenance == SourceObservationRef(
        source_system="incident-management",
        source_record_id="inc-orbit-001",
    )
    assert {
        "file_path",
        "line_number",
        "rule_id",
    }.isdisjoint(field.name for field in fields(Signal))


def test_source_observation_identity_defines_duplicate_signal_semantics() -> None:
    first_ingestion = SourceObservationRef(
        source_system="semgrep",
        source_record_id="repo-borealis-renderer:renderer_client.py:rule:6",
    )
    repeated_ingestion = SourceObservationRef(
        source_system="semgrep",
        source_record_id="repo-borealis-renderer:renderer_client.py:rule:6",
    )
    distinct_incidents = {
        SourceObservationRef("incident-management", "inc-orbit-001"),
        SourceObservationRef("incident-management", "inc-orbit-002"),
        SourceObservationRef("incident-management", "inc-orbit-003"),
    }

    assert repeated_ingestion == first_ingestion
    assert len(distinct_incidents) == 3


def test_evidence_contract_does_not_imply_validation() -> None:
    evidence_fields = {field.name for field in fields(Evidence)}

    assert evidence_fields == {
        "evidence_id",
        "source_system",
        "source_reference",
        "captured_at",
        "reference_uri",
    }
    assert {"validated", "validation_status", "validated_by"}.isdisjoint(
        evidence_fields
    )


def test_canonical_asset_reference_contains_no_governance_or_risk_context() -> None:
    assert {field.name for field in fields(CanonicalAssetRef)} == {
        "asset_key",
        "asset_type",
    }


def test_normalized_signal_contains_only_signal_and_supporting_evidence() -> None:
    assert {field.name for field in fields(NormalizedSignal)} == {
        "signal",
        "evidence",
    }


def test_normalized_signal_rejects_mismatched_evidence() -> None:
    normalized = _normalized_signal(
        signal_id="00000000-0000-0000-0000-000000000103",
        evidence_id="00000000-0000-0000-0000-000000000203",
        source_system="incident-management",
        source_record_id="inc-orbit-001",
        detected_at=datetime(2026, 1, 12, 9, 0, tzinfo=UTC),
        signal_type="OPERATIONAL_INCIDENT",
        asset_key="svc-orbit-catalog",
        asset_type=AssetType.SERVICE,
        severity="MEDIUM",
        source_reference="inc-orbit-001",
    )
    other_evidence = Evidence(
        evidence_id=UUID("00000000-0000-0000-0000-000000000204"),
        source_system="incident-management",
        source_reference="inc-orbit-001",
        captured_at=datetime(2026, 1, 12, 9, 0, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="must match"):
        NormalizedSignal(
            signal=normalized.signal,
            evidence=frozenset({other_evidence}),
        )
