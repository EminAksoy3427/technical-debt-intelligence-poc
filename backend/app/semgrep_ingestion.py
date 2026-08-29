from datetime import datetime
from pathlib import Path
from typing import Final
from urllib.parse import quote
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.assets import CanonicalAssetRef
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Evidence, Signal
from app.infrastructure.semgrep import SemgrepFinding, scan_semgrep_repository
from app.signal_ingestion import NormalizedSignal

SEMGREP_SOURCE_SYSTEM: Final = "semgrep"
SEMGREP_RULE_SIGNAL_TYPES: Final = {
    "tdi.python.hardcoded-endpoint": "HARDCODED_ENDPOINT",
    "tdi.python.missing-timeout": "MISSING_TIMEOUT",
    "tdi.python.process-local-state": "PROCESS_LOCAL_STATE",
}

_SIGNAL_ID_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "technical-debt-intelligence-poc/semgrep/signal",
)
_EVIDENCE_ID_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "technical-debt-intelligence-poc/semgrep/evidence",
)


class UnsupportedSemgrepRuleError(ValueError):
    """Raised when a local Semgrep rule has no approved canonical mapping."""


def scan_and_normalize_semgrep_repository(
    repository_path: Path,
    repository_asset_key: str,
    detected_at: datetime,
    rules_path: Path,
    *,
    executable: str = "semgrep",
) -> tuple[NormalizedSignal, ...]:
    """Scan one known repository and normalize each exact Semgrep observation."""
    findings = scan_semgrep_repository(
        repository_path,
        rules_path,
        executable=executable,
    )
    return tuple(
        normalize_semgrep_finding(
            finding,
            repository_asset_key=repository_asset_key,
            detected_at=detected_at,
        )
        for finding in findings
    )


def normalize_semgrep_finding(
    finding: SemgrepFinding,
    *,
    repository_asset_key: str,
    detected_at: datetime,
) -> NormalizedSignal:
    """Deterministically map one Semgrep finding to the approved Signal contract."""
    if detected_at.tzinfo is None or detected_at.utcoffset() is None:
        raise ValueError("Semgrep detection timestamp must be timezone-aware")

    try:
        signal_type = SEMGREP_RULE_SIGNAL_TYPES[finding.rule_id]
    except KeyError:
        raise UnsupportedSemgrepRuleError(
            f"Semgrep rule has no canonical signal mapping: {finding.rule_id}"
        ) from None

    source_record_id = semgrep_source_record_id(
        finding,
        repository_asset_key=repository_asset_key,
    )
    signal_id = _stable_id(_SIGNAL_ID_NAMESPACE, source_record_id)
    evidence_id = _stable_id(_EVIDENCE_ID_NAMESPACE, source_record_id)
    evidence = Evidence(
        evidence_id=evidence_id,
        source_system=SEMGREP_SOURCE_SYSTEM,
        source_reference=_evidence_reference(
            finding,
            repository_asset_key=repository_asset_key,
        ),
        captured_at=detected_at,
        reference_uri=None,
    )
    signal = Signal(
        signal_id=signal_id,
        source_system=SEMGREP_SOURCE_SYSTEM,
        source_record_id=source_record_id,
        detected_at=detected_at,
        signal_type=signal_type,
        affected_asset=CanonicalAssetRef(
            asset_key=repository_asset_key,
            asset_type=AssetType.REPOSITORY,
        ),
        severity=finding.severity,
        evidence_ids=frozenset({evidence_id}),
    )
    return NormalizedSignal(signal=signal, evidence=frozenset({evidence}))


def semgrep_source_record_id(
    finding: SemgrepFinding,
    *,
    repository_asset_key: str,
) -> str:
    """Build exact observation identity.

    Format:
    asset=<percent-encoded-key>&path=<percent-encoded-relative-path>
    &rule=<percent-encoded-rule>&start=<line>:<column>&end=<line>:<column>
    """
    encoded_asset_key = quote(repository_asset_key, safe="")
    encoded_path = quote(finding.relative_path, safe="")
    encoded_rule_id = quote(finding.rule_id, safe="")
    return (
        f"asset={encoded_asset_key}"
        f"&path={encoded_path}"
        f"&rule={encoded_rule_id}"
        f"&start={finding.start_line}:{finding.start_column}"
        f"&end={finding.end_line}:{finding.end_column}"
    )


def _stable_id(namespace: UUID, source_record_id: str) -> UUID:
    return uuid5(namespace, f"{SEMGREP_SOURCE_SYSTEM}:{source_record_id}")


def _evidence_reference(
    finding: SemgrepFinding,
    *,
    repository_asset_key: str,
) -> str:
    return (
        f"{repository_asset_key}/{finding.relative_path}:"
        f"{finding.start_line}:{finding.start_column}-"
        f"{finding.end_line}:{finding.end_column} "
        f"[{finding.rule_id}] {finding.message}"
    )
