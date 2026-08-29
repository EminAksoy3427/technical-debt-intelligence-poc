import importlib
import inspect
from dataclasses import fields
from datetime import UTC, datetime

import pytest

from app.domain.assets import CanonicalAssetRef
from app.domain.enterprise_estate import AssetType
from app.infrastructure.semgrep import SemgrepFinding
from app.semgrep_ingestion import (
    SEMGREP_RULE_SIGNAL_TYPES,
    UnsupportedSemgrepRuleError,
    normalize_semgrep_finding,
    semgrep_source_record_id,
)
from app.signal_ingestion import NormalizedSignal

DETECTED_AT = datetime(2026, 8, 29, 12, 30, tzinfo=UTC)


def _finding(
    rule_id: str = "tdi.python.missing-timeout",
) -> SemgrepFinding:
    return SemgrepFinding(
        rule_id=rule_id,
        relative_path="src/renderer_client.py",
        start_line=5,
        start_column=10,
        end_line=5,
        end_column=52,
        message="A urllib request is made without an explicit timeout.",
        severity="WARNING",
    )


@pytest.mark.parametrize(
    ("rule_id", "expected_signal_type"),
    [
        ("tdi.python.hardcoded-endpoint", "HARDCODED_ENDPOINT"),
        ("tdi.python.missing-timeout", "MISSING_TIMEOUT"),
        ("tdi.python.process-local-state", "PROCESS_LOCAL_STATE"),
    ],
)
def test_local_rule_ids_map_to_approved_canonical_signal_types(
    rule_id: str,
    expected_signal_type: str,
) -> None:
    normalized = normalize_semgrep_finding(
        _finding(rule_id),
        repository_asset_key="repo-borealis-renderer",
        detected_at=DETECTED_AT,
    )

    assert SEMGREP_RULE_SIGNAL_TYPES[rule_id] == expected_signal_type
    assert normalized.signal.signal_type == expected_signal_type
    assert normalized.signal.source_system == "semgrep"


def test_source_record_id_documents_exact_repository_relative_observation() -> None:
    source_record_id = semgrep_source_record_id(
        _finding(),
        repository_asset_key="repo-borealis-renderer",
    )

    assert source_record_id == (
        "asset=repo-borealis-renderer"
        "&path=src%2Frenderer_client.py"
        "&rule=tdi.python.missing-timeout"
        "&start=5:10"
        "&end=5:52"
    )
    assert "C:" not in source_record_id
    assert "\\" not in source_record_id


def test_same_finding_and_timestamp_normalize_to_identical_ids_and_provenance() -> None:
    finding = _finding()

    first = normalize_semgrep_finding(
        finding,
        repository_asset_key="repo-borealis-renderer",
        detected_at=DETECTED_AT,
    )
    repeated = normalize_semgrep_finding(
        finding,
        repository_asset_key="repo-borealis-renderer",
        detected_at=DETECTED_AT,
    )

    assert repeated.provenance == first.provenance
    assert repeated.signal.signal_id == first.signal.signal_id
    assert repeated.evidence == first.evidence
    assert repeated == first


def test_normalization_preserves_asset_evidence_severity_and_aware_timestamp() -> None:
    normalized = normalize_semgrep_finding(
        _finding(),
        repository_asset_key="repo-borealis-renderer",
        detected_at=DETECTED_AT,
    )
    evidence = next(iter(normalized.evidence))

    assert normalized.signal.affected_asset == CanonicalAssetRef(
        asset_key="repo-borealis-renderer",
        asset_type=AssetType.REPOSITORY,
    )
    assert normalized.signal.detected_at == DETECTED_AT
    assert normalized.signal.detected_at.utcoffset() is not None
    assert normalized.signal.severity == "WARNING"
    assert evidence.captured_at == DETECTED_AT
    assert evidence.source_system == "semgrep"
    assert evidence.reference_uri is None
    assert "repo-borealis-renderer/src/renderer_client.py:5:10-5:52" in (
        evidence.source_reference
    )
    assert "tdi.python.missing-timeout" in evidence.source_reference
    assert evidence.evidence_id in normalized.signal.evidence_ids


def test_normalization_requires_caller_owned_timezone_aware_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        normalize_semgrep_finding(
            _finding(),
            repository_asset_key="repo-borealis-renderer",
            detected_at=datetime(2026, 8, 29, 12, 30),
        )


def test_unknown_semgrep_rule_is_not_silently_normalized() -> None:
    with pytest.raises(UnsupportedSemgrepRuleError, match="no canonical"):
        normalize_semgrep_finding(
            _finding("tdi.python.unmapped"),
            repository_asset_key="repo-borealis-renderer",
            detected_at=DETECTED_AT,
        )


def test_semgrep_ingestion_has_no_candidate_or_ground_truth_contract() -> None:
    normalized_fields = {field.name for field in fields(NormalizedSignal)}
    ingestion_source = inspect.getsource(
        importlib.import_module("app.semgrep_ingestion")
    ).lower()
    boundary_source = inspect.getsource(
        importlib.import_module("app.infrastructure.semgrep")
    ).lower()

    assert normalized_fields == {"signal", "evidence"}
    assert "candidate" not in ingestion_source
    assert "candidate" not in boundary_source
    assert "ground_truth" not in ingestion_source
    assert "ground_truth" not in boundary_source
    assert "datetime.now" not in ingestion_source
