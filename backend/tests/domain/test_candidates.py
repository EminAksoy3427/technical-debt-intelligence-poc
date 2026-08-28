from uuid import UUID, uuid4

import pytest

from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Signal


def create_candidate(
    *,
    signal_ids: frozenset[UUID] | tuple[UUID, ...] | None = None,
    evidence_ids: frozenset[UUID] | tuple[UUID, ...] | None = None,
    hypothesis: str = "Repeated findings indicate a shared structural issue",
    correlation_rationale: str = "Findings affect the same canonical asset",
) -> Candidate:
    return Candidate(
        candidate_id=uuid4(),
        signal_ids=signal_ids if signal_ids is not None else frozenset({uuid4()}),
        evidence_ids=(
            evidence_ids if evidence_ids is not None else frozenset({uuid4()})
        ),
        canonical_asset=CanonicalAssetRef(
            asset_key="repo-synthetic",
            asset_type=AssetType.REPOSITORY,
        ),
        hypothesis=hypothesis,
        correlation_rationale=correlation_rationale,
    )


def test_valid_candidate_can_link_multiple_signals() -> None:
    signal_ids = frozenset({uuid4(), uuid4()})

    candidate = create_candidate(signal_ids=signal_ids)

    assert candidate.signal_ids == signal_ids
    assert candidate.canonical_asset.asset_key == "repo-synthetic"
    assert candidate.canonical_asset.asset_type is AssetType.REPOSITORY


def test_candidate_is_separate_from_signal() -> None:
    candidate = create_candidate()

    assert not isinstance(candidate, Signal)


def test_candidate_rejects_zero_signal_ids() -> None:
    with pytest.raises(ValueError, match="at least one Signal"):
        create_candidate(signal_ids=frozenset())


def test_candidate_rejects_zero_evidence_ids() -> None:
    with pytest.raises(ValueError, match="at least one Evidence"):
        create_candidate(evidence_ids=frozenset())


def test_candidate_rejects_blank_hypothesis() -> None:
    with pytest.raises(ValueError, match="hypothesis"):
        create_candidate(hypothesis="  ")


def test_candidate_rejects_blank_correlation_rationale() -> None:
    with pytest.raises(ValueError, match="correlation rationale"):
        create_candidate(correlation_rationale="\t")


def test_candidate_normalizes_duplicate_linked_identifiers() -> None:
    signal_id = uuid4()
    evidence_id = uuid4()

    candidate = create_candidate(
        signal_ids=(signal_id, signal_id),
        evidence_ids=(evidence_id, evidence_id),
    )

    assert candidate.signal_ids == frozenset({signal_id})
    assert candidate.evidence_ids == frozenset({evidence_id})


def test_canonical_asset_reference_rejects_blank_asset_key() -> None:
    with pytest.raises(ValueError, match="asset key"):
        CanonicalAssetRef(asset_key=" ", asset_type=AssetType.REPOSITORY)
