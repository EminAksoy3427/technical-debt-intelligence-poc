import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import Incident
from app.domain.signals import SourceObservationRef
from app.domain.synthetic_enterprise_estate import (
    SYNTHETIC_ENTERPRISE_ASSETS,
    SYNTHETIC_INCIDENTS,
)
from app.incident_ingestion import normalize_incident
from app.infrastructure.semgrep import scan_semgrep_repository
from app.semgrep_ingestion import normalize_semgrep_finding
from app.signal_ingestion import NormalizedSignal

_INCIDENT_SOURCE_SYSTEM = "incident-management"
_OPERATIONAL_INCIDENT_SIGNAL_TYPE = "OPERATIONAL_INCIDENT"
_RECURRING_INCIDENT_ISSUE_FAMILY = "RECURRING_INCIDENT_PATTERN"
_CASE_FIELDS = {
    "case_key",
    "expected_candidate_group_key",
    "expected_asset_key",
    "issue_family",
    "source_refs",
}


class EvaluationDataError(ValueError):
    """Raised when controlled evaluation data cannot produce valid metrics."""


@dataclass(frozen=True)
class ControlledRepositorySourceRef:
    repository_key: str
    source_file: str


@dataclass(frozen=True)
class IncidentSourceRef:
    incident_key: str


type EvaluationSourceRef = ControlledRepositorySourceRef | IncidentSourceRef


@dataclass(frozen=True)
class GroundTruthCase:
    case_key: str
    expected_candidate_group_key: str
    expected_asset_key: str
    issue_family: str
    source_refs: tuple[EvaluationSourceRef, ...]


@dataclass(frozen=True)
class ResolvedEvaluationCase:
    ground_truth: GroundTruthCase
    normalized_signals: tuple[NormalizedSignal, ...]


@dataclass(frozen=True)
class EvaluationGroup:
    canonical_asset: CanonicalAssetRef
    issue_family: str | None
    source_observations: frozenset[SourceObservationRef]

    def __post_init__(self) -> None:
        observations = frozenset(self.source_observations)
        if not observations:
            raise EvaluationDataError(
                "An evaluation group must contain source observations"
            )
        if self.issue_family is not None and not self.issue_family.strip():
            raise EvaluationDataError(
                "An evaluation issue family must not be blank"
            )
        object.__setattr__(self, "source_observations", observations)


@dataclass(frozen=True)
class CorrelationEvaluationResult:
    expected_group_count: int
    predicted_group_count: int
    true_positive_count: int
    false_positive_count: int
    false_negative_count: int
    precision: float
    recall: float


def load_ground_truth_cases(path: Path) -> tuple[GroundTruthCase, ...]:
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "cases",
    }:
        raise EvaluationDataError("Ground truth has an unexpected top-level schema")
    if payload["schema_version"] != 1:
        raise EvaluationDataError("Ground truth schema_version must be 1")

    raw_cases = payload["cases"]
    if not isinstance(raw_cases, list) or not raw_cases:
        raise EvaluationDataError("Ground truth cases must be a non-empty array")

    cases = tuple(_parse_ground_truth_case(value) for value in raw_cases)
    if len({case.case_key for case in cases}) != len(cases):
        raise EvaluationDataError("Ground truth case keys must be unique")
    if (
        len({case.expected_candidate_group_key for case in cases})
        != len(cases)
    ):
        raise EvaluationDataError(
            "Expected candidate group keys must be unique"
        )
    return cases


def resolve_evaluation_cases(
    cases: tuple[GroundTruthCase, ...],
    *,
    controlled_repository_root: Path,
    semgrep_rules_path: Path,
    detected_at: datetime,
) -> tuple[ResolvedEvaluationCase, ...]:
    assets_by_key = {
        asset.asset_key: CanonicalAssetRef(
            asset_key=asset.asset_key,
            asset_type=asset.asset_type,
        )
        for asset in SYNTHETIC_ENTERPRISE_ASSETS
    }
    incidents_by_key = {
        incident.incident_key: incident for incident in SYNTHETIC_INCIDENTS
    }

    resolved_cases: list[ResolvedEvaluationCase] = []
    observed_provenance: set[SourceObservationRef] = set()
    for case in cases:
        normalized_signals = tuple(
            _resolve_source_ref(
                source_ref,
                controlled_repository_root=controlled_repository_root,
                semgrep_rules_path=semgrep_rules_path,
                detected_at=detected_at,
                assets_by_key=assets_by_key,
                incidents_by_key=incidents_by_key,
            )
            for source_ref in case.source_refs
        )
        provenance = {item.provenance for item in normalized_signals}
        if len(provenance) != len(normalized_signals):
            raise EvaluationDataError(
                f"Case {case.case_key} resolves duplicate source observations"
            )
        if observed_provenance & provenance:
            raise EvaluationDataError(
                "A labelled source observation belongs to multiple cases"
            )
        observed_provenance.update(provenance)
        resolved_cases.append(
            ResolvedEvaluationCase(
                ground_truth=case,
                normalized_signals=normalized_signals,
            )
        )
    return tuple(resolved_cases)


def expected_groups(
    resolved_cases: tuple[ResolvedEvaluationCase, ...],
) -> tuple[EvaluationGroup, ...]:
    groups: list[EvaluationGroup] = []
    for resolved_case in resolved_cases:
        assets = {
            item.signal.affected_asset
            for item in resolved_case.normalized_signals
        }
        if len(assets) != 1:
            raise EvaluationDataError(
                f"Case {resolved_case.ground_truth.case_key} does not resolve "
                "to one canonical asset"
            )
        canonical_asset = next(iter(assets))
        if (
            canonical_asset.asset_key
            != resolved_case.ground_truth.expected_asset_key
        ):
            raise EvaluationDataError(
                f"Case {resolved_case.ground_truth.case_key} expected asset "
                f"{resolved_case.ground_truth.expected_asset_key}, but resolved "
                f"{canonical_asset.asset_key}"
            )
        groups.append(
            EvaluationGroup(
                canonical_asset=canonical_asset,
                issue_family=resolved_case.ground_truth.issue_family,
                source_observations=frozenset(
                    item.provenance
                    for item in resolved_case.normalized_signals
                ),
            )
        )
    return tuple(groups)


def predicted_groups(
    candidates: tuple[Candidate, ...],
    normalized_signals: tuple[NormalizedSignal, ...],
) -> tuple[EvaluationGroup, ...]:
    signals_by_id: dict[UUID, NormalizedSignal] = {}
    for normalized_signal in normalized_signals:
        signal_id = normalized_signal.signal.signal_id
        if signal_id in signals_by_id:
            raise EvaluationDataError(
                f"Duplicate normalized Signal identifier: {signal_id}"
            )
        signals_by_id[signal_id] = normalized_signal

    groups: list[EvaluationGroup] = []
    for candidate in candidates:
        try:
            contributing_signals = tuple(
                signals_by_id[signal_id]
                for signal_id in candidate.signal_ids
            )
        except KeyError as error:
            raise EvaluationDataError(
                f"Candidate references unknown Signal: {error.args[0]}"
            ) from None

        groups.append(
            EvaluationGroup(
                canonical_asset=candidate.canonical_asset,
                issue_family=_predicted_issue_family(
                    candidate,
                    contributing_signals,
                ),
                source_observations=frozenset(
                    item.provenance for item in contributing_signals
                ),
            )
        )
    return tuple(groups)


def evaluate_groups(
    expected: tuple[EvaluationGroup, ...],
    predicted: tuple[EvaluationGroup, ...],
) -> CorrelationEvaluationResult:
    if not expected:
        raise EvaluationDataError(
            "Correlation recall denominator is zero: no expected groups"
        )
    if not predicted:
        raise EvaluationDataError(
            "Correlation precision denominator is zero: no predicted groups"
        )

    expected_counts = Counter(expected)
    predicted_counts = Counter(predicted)
    true_positive_count = sum(
        (expected_counts & predicted_counts).values()
    )
    false_positive_count = len(predicted) - true_positive_count
    false_negative_count = len(expected) - true_positive_count
    precision = true_positive_count / (
        true_positive_count + false_positive_count
    )
    recall = true_positive_count / (
        true_positive_count + false_negative_count
    )
    return CorrelationEvaluationResult(
        expected_group_count=len(expected),
        predicted_group_count=len(predicted),
        true_positive_count=true_positive_count,
        false_positive_count=false_positive_count,
        false_negative_count=false_negative_count,
        precision=precision,
        recall=recall,
    )


def _parse_ground_truth_case(value: object) -> GroundTruthCase:
    if not isinstance(value, dict) or set(value) != _CASE_FIELDS:
        raise EvaluationDataError("Ground truth case has an unexpected schema")
    raw_source_refs = value["source_refs"]
    if not isinstance(raw_source_refs, list) or not raw_source_refs:
        raise EvaluationDataError(
            "Ground truth source_refs must be a non-empty array"
        )
    return GroundTruthCase(
        case_key=_required_string(value, "case_key"),
        expected_candidate_group_key=_required_string(
            value,
            "expected_candidate_group_key",
        ),
        expected_asset_key=_required_string(value, "expected_asset_key"),
        issue_family=_required_string(value, "issue_family"),
        source_refs=tuple(_parse_source_ref(item) for item in raw_source_refs),
    )


def _parse_source_ref(value: object) -> EvaluationSourceRef:
    if not isinstance(value, dict):
        raise EvaluationDataError("Ground truth source_ref must be an object")
    source_type = _required_string(value, "source_type")
    if source_type == "CONTROLLED_REPOSITORY" and set(value) == {
        "source_type",
        "repository_key",
        "source_file",
    }:
        return ControlledRepositorySourceRef(
            repository_key=_required_string(value, "repository_key"),
            source_file=_required_string(value, "source_file"),
        )
    if source_type == "INCIDENT" and set(value) == {
        "source_type",
        "incident_key",
    }:
        return IncidentSourceRef(
            incident_key=_required_string(value, "incident_key")
        )
    raise EvaluationDataError(
        f"Ground truth source_ref has an unexpected {source_type} schema"
    )


def _required_string(value: dict[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise EvaluationDataError(
            f"Ground truth field {key} must be a non-blank string"
        )
    return item


def _resolve_source_ref(
    source_ref: EvaluationSourceRef,
    *,
    controlled_repository_root: Path,
    semgrep_rules_path: Path,
    detected_at: datetime,
    assets_by_key: dict[str, CanonicalAssetRef],
    incidents_by_key: dict[str, Incident],
) -> NormalizedSignal:
    if isinstance(source_ref, ControlledRepositorySourceRef):
        findings = scan_semgrep_repository(
            controlled_repository_root / source_ref.repository_key,
            semgrep_rules_path,
        )
        matching_findings = tuple(
            finding
            for finding in findings
            if finding.relative_path == source_ref.source_file
        )
        if len(matching_findings) != 1:
            raise EvaluationDataError(
                f"Controlled source {source_ref.repository_key}/"
                f"{source_ref.source_file} resolved to "
                f"{len(matching_findings)} Semgrep findings"
            )
        return normalize_semgrep_finding(
            matching_findings[0],
            repository_asset_key=source_ref.repository_key,
            detected_at=detected_at,
        )

    incident = incidents_by_key.get(source_ref.incident_key)
    if incident is None:
        raise EvaluationDataError(
            f"Unknown synthetic incident: {source_ref.incident_key}"
        )
    affected_asset = assets_by_key.get(incident.primary_affected_asset_key)
    if affected_asset is None:
        raise EvaluationDataError(
            f"Unknown incident asset: {incident.primary_affected_asset_key}"
        )
    return normalize_incident(
        incident,
        primary_affected_asset=affected_asset,
    )


def _predicted_issue_family(
    candidate: Candidate,
    normalized_signals: tuple[NormalizedSignal, ...],
) -> str | None:
    signals = tuple(item.signal for item in normalized_signals)
    if not signals or any(
        signal.affected_asset != candidate.canonical_asset
        for signal in signals
    ):
        return None

    if all(
        signal.source_system == _INCIDENT_SOURCE_SYSTEM
        and signal.signal_type == _OPERATIONAL_INCIDENT_SIGNAL_TYPE
        for signal in signals
    ):
        if len(signals) >= 2:
            return _RECURRING_INCIDENT_ISSUE_FAMILY
        return None

    signal_types = {signal.signal_type for signal in signals}
    if (
        all(
            signal.source_system != _INCIDENT_SOURCE_SYSTEM
            for signal in signals
        )
        and len(signal_types) == 1
    ):
        return next(iter(signal_types))
    return None
