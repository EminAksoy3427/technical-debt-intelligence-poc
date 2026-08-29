from typing import Final
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.assets import CanonicalAssetRef
from app.domain.signals import Evidence, Signal
from app.infrastructure.dependency_lifecycle import DependencyLifecycleFinding
from app.signal_ingestion import NormalizedSignal

DEPENDENCY_LIFECYCLE_SOURCE_SYSTEM: Final = "dependency-lifecycle"
DEPENDENCY_EOL_SIGNAL_TYPE: Final = "DEPENDENCY_EOL"

_SIGNAL_ID_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "technical-debt-intelligence-poc/dependency-lifecycle/signal",
)
_EVIDENCE_ID_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "technical-debt-intelligence-poc/dependency-lifecycle/evidence",
)


def normalize_dependency_lifecycle_finding(
    finding: DependencyLifecycleFinding,
    *,
    affected_asset: CanonicalAssetRef,
) -> NormalizedSignal:
    """Deterministically map one lifecycle finding to a canonical Signal."""
    if affected_asset.asset_key != finding.affected_asset_key:
        raise ValueError(
            "Dependency lifecycle affected asset must match the supplied "
            "asset reference"
        )

    source_record_id = finding.source_record_id
    signal_id = _stable_id(_SIGNAL_ID_NAMESPACE, source_record_id)
    evidence_id = _stable_id(_EVIDENCE_ID_NAMESPACE, source_record_id)
    evidence = Evidence(
        evidence_id=evidence_id,
        source_system=DEPENDENCY_LIFECYCLE_SOURCE_SYSTEM,
        source_reference=(
            f"{finding.source_record_id}: {finding.affected_asset_key} "
            f"{finding.component_name} {finding.component_version} "
            f"lifecycle={finding.lifecycle_status.value} "
            f"eol_date={finding.eol_date.isoformat()}; {finding.message}"
        ),
        captured_at=finding.observed_at,
        reference_uri=None,
    )
    signal = Signal(
        signal_id=signal_id,
        source_system=DEPENDENCY_LIFECYCLE_SOURCE_SYSTEM,
        source_record_id=source_record_id,
        detected_at=finding.observed_at,
        signal_type=DEPENDENCY_EOL_SIGNAL_TYPE,
        affected_asset=affected_asset,
        severity=None,
        evidence_ids=frozenset({evidence_id}),
    )
    return NormalizedSignal(signal=signal, evidence=frozenset({evidence}))


def _stable_id(namespace: UUID, source_record_id: str) -> UUID:
    return uuid5(
        namespace,
        f"{DEPENDENCY_LIFECYCLE_SOURCE_SYSTEM}:{source_record_id}",
    )
