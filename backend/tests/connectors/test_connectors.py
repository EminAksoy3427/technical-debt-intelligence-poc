import importlib
import inspect
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.connectors import dependency_lifecycle as dependency_lifecycle_connector
from app.connectors.contracts import (
    ConnectorDescriptor,
    ConnectorRegistration,
    SourceObservation,
)
from app.connectors.dependency_lifecycle import (
    DEPENDENCY_LIFECYCLE_CONNECTOR,
    DEPENDENCY_LIFECYCLE_CONNECTOR_DESCRIPTOR,
    acquire_dependency_lifecycle_observations,
    normalize_dependency_lifecycle_observation,
)
from app.connectors.registry import ConnectorRegistry, get_connector, list_connectors
from app.dependency_lifecycle_ingestion import normalize_dependency_lifecycle_finding
from app.domain.assets import CanonicalAssetRef
from app.domain.enterprise_estate import AssetType
from app.domain.signals import SourceObservationRef
from app.infrastructure.dependency_lifecycle import (
    DependencyLifecycleFinding,
    DependencyLifecycleSourceError,
)
from app.signal_ingestion import NormalizedSignal

SOURCE_PATH = (
    Path(__file__).resolve().parents[3]
    / "synthetic_sources"
    / "dependency_lifecycle_findings.json"
)


def _affected_asset() -> CanonicalAssetRef:
    return CanonicalAssetRef(
        asset_key="repo-borealis-renderer",
        asset_type=AssetType.REPOSITORY,
    )


def test_connector_descriptor_is_immutable_and_has_truthful_metadata() -> None:
    descriptor = DEPENDENCY_LIFECYCLE_CONNECTOR_DESCRIPTOR

    assert descriptor == ConnectorDescriptor(
        connector_id="dependency-lifecycle",
        display_name="Dependency Lifecycle",
        version="1.0.0",
        source_system="dependency-lifecycle",
        transport="local-json",
        read_only=True,
    )
    with pytest.raises(FrozenInstanceError):
        descriptor.display_name = "Changed"  # type: ignore[misc]


def test_source_observation_preserves_provenance_time_and_record() -> None:
    record = object()
    provenance = SourceObservationRef("controlled-source", "record-001")
    observed_at = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)

    observation = SourceObservation(
        provenance=provenance,
        observed_at=observed_at,
        record=record,
    )

    assert observation.provenance is provenance
    assert observation.observed_at is observed_at
    assert observation.observed_at.utcoffset() is not None
    assert observation.record is record


def test_source_observation_rejects_naive_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        SourceObservation(
            provenance=SourceObservationRef("controlled-source", "record-001"),
            observed_at=datetime(2026, 8, 1, 10, 0),
            record=object(),
        )


def test_dependency_lifecycle_connector_acquires_observations_only() -> None:
    observations = DEPENDENCY_LIFECYCLE_CONNECTOR.acquire(SOURCE_PATH)

    assert observations
    assert all(isinstance(item, SourceObservation) for item in observations)
    assert all(
        isinstance(item.record, DependencyLifecycleFinding)
        for item in observations
    )
    assert all(not isinstance(item, NormalizedSignal) for item in observations)
    assert tuple(item.record.source_record_id for item in observations) == (
        "dep-lifecycle-borealis-renderer-001",
    )


def test_dependency_lifecycle_connector_preserves_loader_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = acquire_dependency_lifecycle_observations(SOURCE_PATH)[0].record
    second = replace(first, source_record_id="dep-lifecycle-borealis-renderer-002")
    monkeypatch.setattr(
        dependency_lifecycle_connector,
        "load_dependency_lifecycle_findings",
        lambda _source_path: (second, first),
    )

    observations = acquire_dependency_lifecycle_observations(SOURCE_PATH)

    assert tuple(item.record.source_record_id for item in observations) == (
        "dep-lifecycle-borealis-renderer-002",
        "dep-lifecycle-borealis-renderer-001",
    )


def test_dependency_lifecycle_connector_preserves_source_errors(tmp_path: Path) -> None:
    missing_source = tmp_path / "missing.json"

    with pytest.raises(DependencyLifecycleSourceError, match="could not be read"):
        acquire_dependency_lifecycle_observations(missing_source)


def test_registry_lists_and_resolves_the_reference_connector() -> None:
    registrations = list_connectors()

    assert registrations == (DEPENDENCY_LIFECYCLE_CONNECTOR,)
    assert get_connector("dependency-lifecycle") is DEPENDENCY_LIFECYCLE_CONNECTOR
    assert registrations == list_connectors()


def test_registry_rejects_duplicate_connector_identifiers() -> None:
    duplicate = ConnectorRegistration(
        descriptor=DEPENDENCY_LIFECYCLE_CONNECTOR_DESCRIPTOR,
        acquire=acquire_dependency_lifecycle_observations,
    )

    with pytest.raises(ValueError, match="Duplicate connector identifier"):
        ConnectorRegistry(
            registrations=(DEPENDENCY_LIFECYCLE_CONNECTOR, duplicate),
        )


def test_observation_bridge_preserves_provenance_and_normalization_output() -> None:
    observation = acquire_dependency_lifecycle_observations(SOURCE_PATH)[0]

    bridged = normalize_dependency_lifecycle_observation(
        observation,
        affected_asset=_affected_asset(),
    )
    existing = normalize_dependency_lifecycle_finding(
        observation.record,
        affected_asset=_affected_asset(),
    )

    assert observation.provenance == SourceObservationRef(
        source_system="dependency-lifecycle",
        source_record_id="dep-lifecycle-borealis-renderer-001",
    )
    assert bridged.provenance == observation.provenance
    assert bridged == existing


def test_connector_modules_do_not_depend_on_downstream_or_delivery_concerns() -> None:
    modules = (
        "app.connectors.contracts",
        "app.connectors.dependency_lifecycle",
        "app.connectors.registry",
        "app.infrastructure.dependency_lifecycle",
    )
    source = "\n".join(
        inspect.getsource(importlib.import_module(module)).lower()
        for module in modules
    )

    assert "candidate" not in source
    assert "technicaldebt" not in source
    assert "app.api" not in source
    assert "frontend" not in source
