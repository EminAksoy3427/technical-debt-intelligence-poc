import importlib
import inspect
from dataclasses import fields
from datetime import UTC, datetime
from uuid import UUID

from app.candidate_correlation import correlate_candidates
from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Evidence, Signal
from app.signal_ingestion import NormalizedSignal

_OBSERVED_AT = datetime(2026, 8, 31, 8, 0, tzinfo=UTC)


def _normalized_signal(
    signal_number: int,
    *,
    evidence_numbers: tuple[int, ...] | None = None,
    source_system: str = "semgrep",
    signal_type: str = "MISSING_TIMEOUT",
    asset_key: str = "repo-renderer",
    asset_type: AssetType = AssetType.REPOSITORY,
) -> NormalizedSignal:
    if evidence_numbers is None:
        evidence_numbers = (1000 + signal_number,)

    evidence = frozenset(
        Evidence(
            evidence_id=UUID(int=evidence_number),
            source_system=source_system,
            source_reference=f"evidence-{evidence_number}",
            captured_at=_OBSERVED_AT,
        )
        for evidence_number in evidence_numbers
    )
    signal = Signal(
        signal_id=UUID(int=signal_number),
        source_system=source_system,
        source_record_id=f"observation-{signal_number}",
        detected_at=_OBSERVED_AT,
        signal_type=signal_type,
        affected_asset=CanonicalAssetRef(
            asset_key=asset_key,
            asset_type=asset_type,
        ),
        evidence_ids=frozenset(item.evidence_id for item in evidence),
    )
    return NormalizedSignal(signal=signal, evidence=evidence)


def _operational_incident(
    signal_number: int,
    *,
    asset_key: str = "service-catalog",
) -> NormalizedSignal:
    return _normalized_signal(
        signal_number,
        source_system="incident-management",
        signal_type="OPERATIONAL_INCIDENT",
        asset_key=asset_key,
        asset_type=AssetType.SERVICE,
    )


def test_single_non_incident_signal_creates_candidate() -> None:
    normalized = _normalized_signal(1)

    candidates = correlate_candidates((normalized,))

    assert len(candidates) == 1
    assert candidates[0].signal_ids == frozenset({normalized.signal.signal_id})
    assert candidates[0].canonical_asset == normalized.signal.affected_asset
    assert candidates[0].hypothesis == (
        "Potential MISSING_TIMEOUT issue affecting repo-renderer"
    )
    assert candidates[0].correlation_rationale


def test_candidate_id_is_deterministic_and_independent_of_group_membership() -> None:
    first_signal = _normalized_signal(1)
    second_signal = _normalized_signal(2)

    first_call = correlate_candidates((first_signal,))
    repeated_call = correlate_candidates((first_signal,))
    expanded_group = correlate_candidates((first_signal, second_signal))

    assert first_call[0].candidate_id == repeated_call[0].candidate_id
    assert first_call[0].candidate_id == expanded_group[0].candidate_id


def test_candidate_correlation_and_order_are_input_order_independent() -> None:
    normalized_signals = (
        _normalized_signal(1, signal_type="DEPENDENCY_EOL"),
        _normalized_signal(2, asset_key="repo-api"),
        _normalized_signal(3),
    )

    forward = correlate_candidates(normalized_signals)
    reversed_input = correlate_candidates(reversed(normalized_signals))

    assert reversed_input == forward


def test_same_asset_and_problem_family_correlate_with_exact_membership() -> None:
    first = _normalized_signal(1, evidence_numbers=(101, 102))
    second = _normalized_signal(2, evidence_numbers=(103,))

    (candidate,) = correlate_candidates((first, second))

    assert candidate.signal_ids == frozenset(
        {first.signal.signal_id, second.signal.signal_id}
    )
    assert candidate.evidence_ids == frozenset(
        {
            UUID(int=101),
            UUID(int=102),
            UUID(int=103),
        }
    )


def test_different_canonical_assets_do_not_correlate() -> None:
    first = _normalized_signal(1, asset_key="repo-renderer")
    second = _normalized_signal(2, asset_key="repo-api")

    candidates = correlate_candidates((first, second))

    assert len(candidates) == 2
    assert {candidate.canonical_asset.asset_key for candidate in candidates} == {
        "repo-renderer",
        "repo-api",
    }


def test_asset_type_is_part_of_canonical_correlation_identity() -> None:
    repository_signal = _normalized_signal(1, asset_key="shared-key")
    service_signal = _normalized_signal(
        2,
        asset_key="shared-key",
        asset_type=AssetType.SERVICE,
    )

    candidates = correlate_candidates((repository_signal, service_signal))

    assert len(candidates) == 2
    assert len({candidate.candidate_id for candidate in candidates}) == 2


def test_different_problem_families_on_same_asset_remain_separate() -> None:
    missing_timeout = _normalized_signal(1, signal_type="MISSING_TIMEOUT")
    dependency_eol = _normalized_signal(
        2,
        source_system="dependency-lifecycle",
        signal_type="DEPENDENCY_EOL",
    )

    candidates = correlate_candidates((missing_timeout, dependency_eol))

    assert len(candidates) == 2
    assert {candidate.signal_ids for candidate in candidates} == {
        frozenset({missing_timeout.signal.signal_id}),
        frozenset({dependency_eol.signal.signal_id}),
    }


def test_recurring_incidents_on_same_asset_form_one_candidate() -> None:
    first = _operational_incident(1)
    second = _operational_incident(2)

    (candidate,) = correlate_candidates((first, second))

    assert candidate.signal_ids == frozenset(
        {first.signal.signal_id, second.signal.signal_id}
    )
    assert "recurring operational incident pattern" in candidate.hypothesis
    assert "2 distinct OPERATIONAL_INCIDENT Signals" in (
        candidate.correlation_rationale
    )
    assert "does not establish a common root cause" in candidate.correlation_rationale


def test_single_operational_incident_does_not_create_candidate() -> None:
    assert correlate_candidates((_operational_incident(1),)) == ()


def test_repeated_identical_incident_does_not_satisfy_recurrence_threshold() -> None:
    incident = _operational_incident(1)

    assert correlate_candidates((incident, incident)) == ()


def test_operational_incidents_on_different_assets_never_correlate() -> None:
    first_asset_incidents = (
        _operational_incident(1, asset_key="service-catalog"),
        _operational_incident(2, asset_key="service-catalog"),
    )
    second_asset_incidents = (
        _operational_incident(3, asset_key="service-orders"),
        _operational_incident(4, asset_key="service-orders"),
    )

    candidates = correlate_candidates((*first_asset_incidents, *second_asset_incidents))

    assert len(candidates) == 2
    assert {candidate.signal_ids for candidate in candidates} == {
        frozenset(item.signal.signal_id for item in first_asset_incidents),
        frozenset(item.signal.signal_id for item in second_asset_incidents),
    }


def test_candidate_generation_does_not_add_lifecycle_decision_state() -> None:
    (candidate,) = correlate_candidates((_normalized_signal(1),))
    candidate_fields = {field.name for field in fields(candidate)}

    assert isinstance(candidate, Candidate)
    assert candidate_fields == {
        "candidate_id",
        "signal_ids",
        "evidence_ids",
        "canonical_asset",
        "hypothesis",
        "correlation_rationale",
    }
    assert {
        "status",
        "risk",
        "effort",
        "owner",
        "suggested_owner",
        "validation",
        "validated",
        "technical_debt",
    }.isdisjoint(candidate_fields)


def test_runtime_correlation_source_is_isolated_from_evaluation_ground_truth() -> None:
    source = inspect.getsource(
        importlib.import_module("app.candidate_correlation")
    ).lower()

    assert "ground_truth" not in source
    assert "correlation_cases.json" not in source
    assert "evaluation/ground_truth" not in source
