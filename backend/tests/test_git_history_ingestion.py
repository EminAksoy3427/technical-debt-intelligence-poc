import importlib
import inspect
from dataclasses import fields
from datetime import UTC, datetime

from app.domain.assets import CanonicalAssetRef
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Evidence, Signal, SourceObservationRef
from app.git_history_ingestion import (
    GIT_SATD_SIGNAL_TYPE,
    GIT_SOURCE_SYSTEM,
    git_source_record_id,
    normalize_git_satd_finding,
    scan_and_normalize_git_repository,
)
from app.infrastructure.git_history import GitSatdFinding, scan_git_satd_comments
from app.signal_ingestion import NormalizedSignal

REPOSITORY_ASSET_KEY = "repo-borealis-renderer"


def _finding(controlled_git_repository) -> GitSatdFinding:
    return scan_git_satd_comments(controlled_git_repository.path)[0]


def test_git_observation_normalizes_to_approved_canonical_signal(
    controlled_git_repository,
) -> None:
    finding = _finding(controlled_git_repository)
    normalized = normalize_git_satd_finding(
        finding,
        repository_asset_key=REPOSITORY_ASSET_KEY,
    )

    assert normalized.signal.source_system == GIT_SOURCE_SYSTEM == "git"
    assert normalized.signal.signal_type == (
        GIT_SATD_SIGNAL_TYPE
    ) == "SATD_COMMENT_ADDED"
    assert normalized.provenance == SourceObservationRef(
        source_system="git",
        source_record_id=normalized.signal.source_record_id,
    )


def test_git_source_record_id_is_exact_observation_identity(
    controlled_git_repository,
) -> None:
    finding = _finding(controlled_git_repository)
    source_record_id = git_source_record_id(
        finding,
        repository_asset_key=REPOSITORY_ASSET_KEY,
    )

    assert finding.added_line == 10
    assert source_record_id == (
        "asset=repo-borealis-renderer"
        f"&commit={controlled_git_repository.satd_commit_hash}"
        "&path=renderer_client.py"
        "&line=10"
        "&kind=satd-comment"
    )
    assert str(controlled_git_repository.path) not in source_record_id
    assert "C:" not in source_record_id
    assert "\\" not in source_record_id


def test_source_record_id_percent_encodes_asset_and_path() -> None:
    finding = GitSatdFinding(
        commit_hash="a" * 40,
        relative_path="src/renderer client.py",
        added_line=12,
        comment_text="# TECH DEBT: remove compatibility layer",
        commit_timestamp=_aware_timestamp(),
    )

    assert git_source_record_id(
        finding,
        repository_asset_key="repo/borealis renderer",
    ) == (
        "asset=repo%2Fborealis%20renderer"
        f"&commit={'a' * 40}"
        "&path=src%2Frenderer%20client.py"
        "&line=12"
        "&kind=satd-comment"
    )


def test_same_git_finding_has_deterministic_provenance_and_ids(
    controlled_git_repository,
) -> None:
    finding = _finding(controlled_git_repository)
    first = normalize_git_satd_finding(
        finding,
        repository_asset_key=REPOSITORY_ASSET_KEY,
    )
    repeated = normalize_git_satd_finding(
        finding,
        repository_asset_key=REPOSITORY_ASSET_KEY,
    )
    first_evidence = next(iter(first.evidence))

    assert repeated.provenance == first.provenance
    assert repeated.signal.signal_id == first.signal.signal_id
    assert repeated.evidence == first.evidence
    assert repeated == first
    assert first.signal.signal_id != first_evidence.evidence_id


def test_git_timestamp_asset_severity_and_evidence_are_preserved(
    controlled_git_repository,
) -> None:
    finding = _finding(controlled_git_repository)
    normalized = normalize_git_satd_finding(
        finding,
        repository_asset_key=REPOSITORY_ASSET_KEY,
    )
    evidence = next(iter(normalized.evidence))

    assert normalized.signal.detected_at is finding.commit_timestamp
    assert evidence.captured_at is finding.commit_timestamp
    assert normalized.signal.detected_at == controlled_git_repository.satd_timestamp
    assert normalized.signal.affected_asset == CanonicalAssetRef(
        asset_key=REPOSITORY_ASSET_KEY,
        asset_type=AssetType.REPOSITORY,
    )
    assert normalized.signal.severity is None
    assert evidence.source_system == "git"
    assert evidence.reference_uri is None
    assert REPOSITORY_ASSET_KEY in evidence.source_reference
    assert finding.commit_hash in evidence.source_reference
    assert f"{finding.relative_path}:{finding.added_line}" in (
        evidence.source_reference
    )
    assert finding.comment_text in evidence.source_reference
    assert len(evidence.source_reference) < 300
    assert "validated" not in evidence.source_reference.lower()
    assert "risk" not in evidence.source_reference.lower()


def test_scan_and_normalize_entire_repository_returns_one_signal(
    controlled_git_repository,
) -> None:
    normalized_signals = scan_and_normalize_git_repository(
        controlled_git_repository.path,
        repository_asset_key=REPOSITORY_ASSET_KEY,
    )

    assert len(normalized_signals) == 1
    assert normalized_signals[0].signal.source_system == "git"
    assert normalized_signals[0].signal.signal_type == "SATD_COMMENT_ADDED"


def test_git_boundary_does_not_leak_into_canonical_contracts() -> None:
    signal_fields = {field.name for field in fields(Signal)}
    normalized_fields = {field.name for field in fields(NormalizedSignal)}
    evidence_fields = {field.name for field in fields(Evidence)}
    ingestion_source = inspect.getsource(
        importlib.import_module("app.git_history_ingestion")
    ).lower()
    source_boundary = inspect.getsource(
        importlib.import_module("app.infrastructure.git_history")
    ).lower()

    assert {
        "commit_hash",
        "relative_path",
        "added_line",
        "comment_text",
        "commit_timestamp",
    }.isdisjoint(signal_fields)
    assert normalized_fields == {"signal", "evidence"}
    assert {"validated", "validation_status", "validated_by"}.isdisjoint(
        evidence_fields
    )
    assert "candidate" not in ingestion_source
    assert "candidate" not in source_boundary
    assert "technicaldebt" not in ingestion_source
    assert "technicaldebt" not in source_boundary
    assert "ground_truth" not in ingestion_source
    assert "ground_truth" not in source_boundary
    assert "datetime.now" not in ingestion_source
    assert "datetime.now" not in source_boundary


def _aware_timestamp() -> datetime:
    return datetime(2026, 8, 21, 11, 30, tzinfo=UTC)
