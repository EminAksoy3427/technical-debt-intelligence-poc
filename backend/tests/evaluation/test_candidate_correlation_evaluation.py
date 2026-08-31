from datetime import UTC, datetime
from pathlib import Path

import pytest
from correlation_evaluation import (
    CorrelationEvaluationResult,
    EvaluationDataError,
    EvaluationGroup,
    evaluate_groups,
    expected_groups,
    load_ground_truth_cases,
    predicted_groups,
    resolve_evaluation_cases,
)

from app.candidate_correlation import correlate_candidates
from app.domain.assets import CanonicalAssetRef
from app.domain.enterprise_estate import AssetType
from app.domain.signals import SourceObservationRef

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"
GROUND_TRUTH_PATH = (
    PROJECT_ROOT / "evaluation" / "ground_truth" / "correlation_cases.json"
)
CONTROLLED_REPOSITORY_ROOT = PROJECT_ROOT / "synthetic_repositories"
SEMGREP_RULES_PATH = BACKEND_ROOT / "semgrep" / "rules.yml"
DETECTED_AT = datetime(2026, 8, 31, 8, 0, tzinfo=UTC)
PRECISION_TARGET = 0.90
RECALL_TARGET = 0.80


def _group(
    *observation_ids: str,
    asset_key: str = "repo-example",
    issue_family: str = "MISSING_TIMEOUT",
) -> EvaluationGroup:
    return EvaluationGroup(
        canonical_asset=CanonicalAssetRef(
            asset_key=asset_key,
            asset_type=AssetType.REPOSITORY,
        ),
        issue_family=issue_family,
        source_observations=frozenset(
            SourceObservationRef(
                source_system="controlled-test",
                source_record_id=observation_id,
            )
            for observation_id in observation_ids
        ),
    )


def test_perfect_group_matching_has_perfect_precision_and_recall() -> None:
    first = _group("A")
    second = _group("B", asset_key="repo-second")

    result = evaluate_groups((first, second), (first, second))

    assert result == CorrelationEvaluationResult(
        expected_group_count=2,
        predicted_group_count=2,
        true_positive_count=2,
        false_positive_count=0,
        false_negative_count=0,
        precision=1.0,
        recall=1.0,
    )


def test_one_unmatched_prediction_reduces_precision() -> None:
    expected = _group("A")

    result = evaluate_groups(
        (expected,),
        (expected, _group("B", asset_key="repo-unmatched")),
    )

    assert result.true_positive_count == 1
    assert result.false_positive_count == 1
    assert result.false_negative_count == 0
    assert result.precision == 0.5
    assert result.recall == 1.0


def test_one_missing_expected_group_reduces_recall() -> None:
    matched = _group("A")
    missing = _group("B", asset_key="repo-missing")

    result = evaluate_groups((matched, missing), (matched,))

    assert result.true_positive_count == 1
    assert result.false_positive_count == 0
    assert result.false_negative_count == 1
    assert result.precision == 1.0
    assert result.recall == 0.5


def test_false_split_is_not_a_correct_group_match() -> None:
    result = evaluate_groups(
        (_group("A", "B", "C"),),
        (_group("A", "B"), _group("C")),
    )

    assert result.true_positive_count == 0
    assert result.false_positive_count == 2
    assert result.false_negative_count == 1
    assert result.precision == 0.0
    assert result.recall == 0.0


def test_false_merge_is_not_a_correct_group_match() -> None:
    result = evaluate_groups(
        (_group("A"), _group("B")),
        (_group("A", "B"),),
    )

    assert result.true_positive_count == 0
    assert result.false_positive_count == 1
    assert result.false_negative_count == 2
    assert result.precision == 0.0
    assert result.recall == 0.0


def test_asset_mismatch_prevents_an_otherwise_exact_match() -> None:
    result = evaluate_groups(
        (_group("A", asset_key="repo-expected"),),
        (_group("A", asset_key="repo-predicted"),),
    )

    assert result.true_positive_count == 0
    assert result.false_positive_count == 1
    assert result.false_negative_count == 1


def test_issue_family_mismatch_prevents_an_otherwise_exact_match() -> None:
    result = evaluate_groups(
        (_group("A", issue_family="MISSING_TIMEOUT"),),
        (_group("A", issue_family="HARDCODED_ENDPOINT"),),
    )

    assert result.true_positive_count == 0
    assert result.false_positive_count == 1
    assert result.false_negative_count == 1


def test_group_order_does_not_affect_metrics() -> None:
    first = _group("A")
    second = _group("B", asset_key="repo-second")
    unmatched = _group("C", asset_key="repo-unmatched")

    forward = evaluate_groups(
        (first, second),
        (first, second, unmatched),
    )
    reversed_order = evaluate_groups(
        (second, first),
        (unmatched, second, first),
    )

    assert reversed_order == forward


def test_empty_metric_denominators_are_explicit_evaluation_errors() -> None:
    with pytest.raises(EvaluationDataError, match="recall denominator"):
        evaluate_groups((), (_group("A"),))

    with pytest.raises(EvaluationDataError, match="precision denominator"):
        evaluate_groups((_group("A"),), ())


def test_real_controlled_correlation_meets_poc_acceptance_targets() -> None:
    cases = load_ground_truth_cases(GROUND_TRUTH_PATH)
    resolved_cases = resolve_evaluation_cases(
        cases,
        controlled_repository_root=CONTROLLED_REPOSITORY_ROOT,
        semgrep_rules_path=SEMGREP_RULES_PATH,
        detected_at=DETECTED_AT,
    )
    normalized_signals = tuple(
        normalized_signal
        for resolved_case in resolved_cases
        for normalized_signal in resolved_case.normalized_signals
    )

    candidates = correlate_candidates(normalized_signals)
    predictions = predicted_groups(candidates, normalized_signals)
    expectations = expected_groups(resolved_cases)
    result = evaluate_groups(expectations, predictions)

    assert len(normalized_signals) == 6
    assert result == CorrelationEvaluationResult(
        expected_group_count=4,
        predicted_group_count=4,
        true_positive_count=4,
        false_positive_count=0,
        false_negative_count=0,
        precision=1.0,
        recall=1.0,
    )
    assert result.precision >= PRECISION_TARGET
    assert result.recall >= RECALL_TARGET
