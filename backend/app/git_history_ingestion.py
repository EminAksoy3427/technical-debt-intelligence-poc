from pathlib import Path
from typing import Final
from urllib.parse import quote
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.assets import CanonicalAssetRef
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Evidence, Signal
from app.infrastructure.git_history import GitSatdFinding, scan_git_satd_comments
from app.signal_ingestion import NormalizedSignal

GIT_SOURCE_SYSTEM: Final = "git"
GIT_SATD_SIGNAL_TYPE: Final = "SATD_COMMENT_ADDED"

_SIGNAL_ID_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "technical-debt-intelligence-poc/git/signal",
)
_EVIDENCE_ID_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "technical-debt-intelligence-poc/git/evidence",
)


def scan_and_normalize_git_repository(
    repository_path: Path,
    *,
    repository_asset_key: str,
) -> tuple[NormalizedSignal, ...]:
    """Scan one known Git repository and normalize its explicit SATD comments."""
    return tuple(
        normalize_git_satd_finding(
            finding,
            repository_asset_key=repository_asset_key,
        )
        for finding in scan_git_satd_comments(repository_path)
    )


def normalize_git_satd_finding(
    finding: GitSatdFinding,
    *,
    repository_asset_key: str,
) -> NormalizedSignal:
    """Deterministically map one Git SATD observation to a canonical Signal."""
    source_record_id = git_source_record_id(
        finding,
        repository_asset_key=repository_asset_key,
    )
    signal_id = _stable_id(_SIGNAL_ID_NAMESPACE, source_record_id)
    evidence_id = _stable_id(_EVIDENCE_ID_NAMESPACE, source_record_id)
    evidence = Evidence(
        evidence_id=evidence_id,
        source_system=GIT_SOURCE_SYSTEM,
        source_reference=(
            f"{repository_asset_key}@{finding.commit_hash} "
            f"{finding.relative_path}:{finding.added_line} "
            f"{finding.comment_text}"
        ),
        captured_at=finding.commit_timestamp,
        reference_uri=None,
    )
    signal = Signal(
        signal_id=signal_id,
        source_system=GIT_SOURCE_SYSTEM,
        source_record_id=source_record_id,
        detected_at=finding.commit_timestamp,
        signal_type=GIT_SATD_SIGNAL_TYPE,
        affected_asset=CanonicalAssetRef(
            asset_key=repository_asset_key,
            asset_type=AssetType.REPOSITORY,
        ),
        severity=None,
        evidence_ids=frozenset({evidence_id}),
    )
    return NormalizedSignal(signal=signal, evidence=frozenset({evidence}))


def git_source_record_id(
    finding: GitSatdFinding,
    *,
    repository_asset_key: str,
) -> str:
    """Build exact Git observation identity from stable public source facts."""
    if not repository_asset_key.strip():
        raise ValueError("Git repository asset key must not be blank")

    encoded_asset_key = quote(repository_asset_key, safe="")
    encoded_path = quote(finding.relative_path, safe="")
    return (
        f"asset={encoded_asset_key}"
        f"&commit={finding.commit_hash}"
        f"&path={encoded_path}"
        f"&line={finding.added_line}"
        "&kind=satd-comment"
    )


def _stable_id(namespace: UUID, source_record_id: str) -> UUID:
    return uuid5(namespace, f"{GIT_SOURCE_SYSTEM}:{source_record_id}")
