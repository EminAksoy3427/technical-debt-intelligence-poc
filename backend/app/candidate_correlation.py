import json
from collections.abc import Iterable
from typing import Final
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.signal_ingestion import NormalizedSignal

_INCIDENT_SOURCE_SYSTEM: Final = "incident-management"
_OPERATIONAL_INCIDENT_SIGNAL_TYPE: Final = "OPERATIONAL_INCIDENT"
_RECURRING_INCIDENT_PROBLEM_FAMILY: Final = "RECURRING_INCIDENT_PATTERN"

_CANDIDATE_ID_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "technical-debt-intelligence-poc/candidate-correlation/candidate",
)


def correlate_candidates(
    normalized_signals: Iterable[NormalizedSignal],
) -> tuple[Candidate, ...]:
    """Correlate canonical Signals into deterministic problem hypotheses."""
    grouped_evidence: dict[
        tuple[AssetType, str, str],
        dict[UUID, frozenset[UUID]],
    ] = {}

    for normalized_signal in normalized_signals:
        signal = normalized_signal.signal
        problem_family = _problem_family(normalized_signal)
        group_key = (
            signal.affected_asset.asset_type,
            signal.affected_asset.asset_key,
            problem_family,
        )
        evidence_by_signal = grouped_evidence.setdefault(group_key, {})
        evidence_by_signal[signal.signal_id] = (
            evidence_by_signal.get(signal.signal_id, frozenset())
            | signal.evidence_ids
        )

    candidates: list[Candidate] = []
    for group_key, evidence_by_signal in sorted(
        grouped_evidence.items(),
        key=lambda item: (
            item[0][0].value,
            item[0][1],
            item[0][2],
        ),
    ):
        asset_type, asset_key, problem_family = group_key
        signal_ids = frozenset(evidence_by_signal)

        if (
            problem_family == _RECURRING_INCIDENT_PROBLEM_FAMILY
            and len(signal_ids) < 2
        ):
            continue

        evidence_ids = frozenset(
            evidence_id
            for signal_evidence_ids in evidence_by_signal.values()
            for evidence_id in signal_evidence_ids
        )
        candidates.append(
            Candidate(
                candidate_id=_candidate_id(
                    asset_type=asset_type,
                    asset_key=asset_key,
                    problem_family=problem_family,
                ),
                signal_ids=signal_ids,
                evidence_ids=evidence_ids,
                canonical_asset=CanonicalAssetRef(
                    asset_key=asset_key,
                    asset_type=asset_type,
                ),
                hypothesis=_hypothesis(
                    asset_key=asset_key,
                    problem_family=problem_family,
                ),
                correlation_rationale=_correlation_rationale(
                    signal_count=len(signal_ids),
                    problem_family=problem_family,
                ),
            )
        )

    return tuple(candidates)


def _problem_family(normalized_signal: NormalizedSignal) -> str:
    signal = normalized_signal.signal
    if (
        signal.source_system == _INCIDENT_SOURCE_SYSTEM
        and signal.signal_type == _OPERATIONAL_INCIDENT_SIGNAL_TYPE
    ):
        return _RECURRING_INCIDENT_PROBLEM_FAMILY
    return signal.signal_type


def _candidate_id(
    *,
    asset_type: AssetType,
    asset_key: str,
    problem_family: str,
) -> UUID:
    canonical_group_key = json.dumps(
        {
            "asset_key": asset_key,
            "asset_type": asset_type.value,
            "problem_family": problem_family,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return uuid5(_CANDIDATE_ID_NAMESPACE, canonical_group_key)


def _hypothesis(*, asset_key: str, problem_family: str) -> str:
    if problem_family == _RECURRING_INCIDENT_PROBLEM_FAMILY:
        return (
            "Potential recurring operational incident pattern affecting "
            f"{asset_key}"
        )
    return f"Potential {problem_family} issue affecting {asset_key}"


def _correlation_rationale(*, signal_count: int, problem_family: str) -> str:
    if problem_family == _RECURRING_INCIDENT_PROBLEM_FAMILY:
        return (
            f"{signal_count} distinct OPERATIONAL_INCIDENT Signals from "
            "incident-management affect the same canonical asset; this deterministic "
            "recurrence heuristic does not establish a common root cause."
        )
    return (
        f"{signal_count} distinct Signal(s) affect the same canonical asset and share "
        f"the exact signal type/problem family {problem_family}."
    )
