from datetime import UTC, datetime
from uuid import UUID

from app.actions.composition import (
    compose_github_issue_body,
    compose_github_issue_title,
)
from app.domain.action_proposals import action_proposal_reconciliation_marker
from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.technical_debts import TechnicalDebt, TechnicalDebtLifecycleStatus

CREATED_AT = datetime(2026, 9, 7, 14, 0, tzinfo=UTC)
CANDIDATE_ID = UUID("00000000-0000-0000-0000-000000000721")
SIGNAL_ID = UUID("00000000-0000-0000-0000-000000000221")
EVIDENCE_ID = UUID("00000000-0000-0000-0000-000000000321")
TECHNICAL_DEBT_ID = UUID("00000000-0000-0000-0000-000000000911")
DECISION_ID = UUID("00000000-0000-0000-0000-000000000811")
PROPOSAL_ID = UUID("00000000-0000-0000-0000-000000000501")


def _candidate() -> Candidate:
    return Candidate(
        candidate_id=CANDIDATE_ID,
        signal_ids=frozenset({SIGNAL_ID}),
        evidence_ids=frozenset({EVIDENCE_ID}),
        canonical_asset=CanonicalAssetRef(
            asset_key="repo-borealis-renderer",
            asset_type=AssetType.REPOSITORY,
        ),
        hypothesis="Potential missing request timeout",
        correlation_rationale="Persisted Signals share an asset and problem family.",
    )


def _technical_debt() -> TechnicalDebt:
    return TechnicalDebt(
        technical_debt_id=TECHNICAL_DEBT_ID,
        source_candidate_id=CANDIDATE_ID,
        creation_human_decision_id=DECISION_ID,
        lifecycle_status=TechnicalDebtLifecycleStatus.REGISTERED,
        created_at=CREATED_AT,
    )


def test_issue_title_is_deterministic_from_persisted_candidate_truth() -> None:
    candidate = _candidate()

    first_title = compose_github_issue_title(candidate)
    assert first_title == "Technical debt: repo-borealis-renderer"
    assert first_title == compose_github_issue_title(candidate)


def test_issue_body_is_deterministic_and_embeds_the_reconciliation_marker() -> None:
    technical_debt = _technical_debt()
    candidate = _candidate()
    marker = action_proposal_reconciliation_marker(PROPOSAL_ID)

    body = compose_github_issue_body(
        technical_debt=technical_debt,
        candidate=candidate,
        action_proposal_id=PROPOSAL_ID,
    )

    assert body == (
        "Technical debt remediation tracking issue\n"
        "\n"
        f"technical_debt_id: {TECHNICAL_DEBT_ID}\n"
        f"source_candidate_id: {CANDIDATE_ID}\n"
        "canonical_asset: repo-borealis-renderer (REPOSITORY)\n"
        "hypothesis: Potential missing request timeout\n"
        "\n"
        f"{marker}\n"
    )
    assert compose_github_issue_body(
        technical_debt=technical_debt,
        candidate=candidate,
        action_proposal_id=PROPOSAL_ID,
    ) == body
    assert "risk" not in body.lower()
    assert "effort" not in body.lower()
    assert "priority" not in body.lower()
    assert "owner" not in body.lower()
