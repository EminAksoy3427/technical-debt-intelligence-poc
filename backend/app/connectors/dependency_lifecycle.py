from pathlib import Path
from typing import Final

from app.connectors.contracts import (
    ConnectorDescriptor,
    ConnectorRegistration,
    SourceObservation,
)
from app.dependency_lifecycle_ingestion import (
    DEPENDENCY_LIFECYCLE_SOURCE_SYSTEM,
    normalize_dependency_lifecycle_finding,
)
from app.domain.assets import CanonicalAssetRef
from app.domain.signals import SourceObservationRef
from app.infrastructure.dependency_lifecycle import (
    DependencyLifecycleFinding,
    load_dependency_lifecycle_findings,
)
from app.signal_ingestion import NormalizedSignal

DEPENDENCY_LIFECYCLE_CONNECTOR_DESCRIPTOR: Final = ConnectorDescriptor(
    connector_id="dependency-lifecycle",
    display_name="Dependency Lifecycle",
    version="1.0.0",
    source_system=DEPENDENCY_LIFECYCLE_SOURCE_SYSTEM,
    transport="local-json",
    read_only=True,
)


def acquire_dependency_lifecycle_observations(
    source_path: Path,
) -> tuple[SourceObservation[DependencyLifecycleFinding], ...]:
    """Acquire lifecycle findings without performing canonical normalization."""
    findings = load_dependency_lifecycle_findings(source_path)
    return tuple(
        SourceObservation(
            provenance=SourceObservationRef(
                source_system=DEPENDENCY_LIFECYCLE_SOURCE_SYSTEM,
                source_record_id=finding.source_record_id,
            ),
            observed_at=finding.observed_at,
            record=finding,
        )
        for finding in findings
    )


def normalize_dependency_lifecycle_observation(
    observation: SourceObservation[DependencyLifecycleFinding],
    *,
    affected_asset: CanonicalAssetRef,
) -> NormalizedSignal:
    """Map an acquired observation through the existing canonical normalizer."""
    finding = observation.record
    expected_provenance = SourceObservationRef(
        source_system=DEPENDENCY_LIFECYCLE_SOURCE_SYSTEM,
        source_record_id=finding.source_record_id,
    )
    if observation.provenance != expected_provenance:
        raise ValueError(
            "Dependency lifecycle observation provenance must match record"
        )
    if observation.observed_at != finding.observed_at:
        raise ValueError("Dependency lifecycle observation time must match record")

    normalized = normalize_dependency_lifecycle_finding(
        finding,
        affected_asset=affected_asset,
    )
    if normalized.provenance != observation.provenance:
        raise ValueError("Dependency lifecycle normalization must preserve provenance")
    return normalized


DEPENDENCY_LIFECYCLE_CONNECTOR: Final = ConnectorRegistration(
    descriptor=DEPENDENCY_LIFECYCLE_CONNECTOR_DESCRIPTOR,
    acquire=acquire_dependency_lifecycle_observations,
)
