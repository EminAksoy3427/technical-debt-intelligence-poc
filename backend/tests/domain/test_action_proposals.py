from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.domain.action_proposals import (
    ActionProposal,
    ActionType,
    GitHubIssuePayload,
    action_proposal_reconciliation_marker,
    canonical_action_payload_fingerprint,
)
from app.domain.candidates import Candidate
from app.domain.human_decisions import HumanDecision
from app.domain.technical_debts import TechnicalDebt

CREATED_AT = datetime(2026, 9, 7, 14, 0, tzinfo=UTC)
PROPOSAL_ID = UUID("00000000-0000-0000-0000-000000000501")
TECHNICAL_DEBT_ID = UUID("00000000-0000-0000-0000-000000000911")


def _payload(
    *,
    action_proposal_id: UUID = PROPOSAL_ID,
    title: str = "Technical debt: repo-borealis-renderer",
    body_prefix: str = "Technical debt remediation tracking issue\n\n",
) -> GitHubIssuePayload:
    marker = action_proposal_reconciliation_marker(action_proposal_id)
    return GitHubIssuePayload(title=title, body=f"{body_prefix}{marker}\n")


def _fingerprint(
    payload: GitHubIssuePayload,
    *,
    action_type: str = ActionType.CREATE_GITHUB_ISSUE.value,
    target_repository_owner: str = "tdi-demo-target",
    target_repository_name: str = "tdi-action-preview",
) -> str:
    return canonical_action_payload_fingerprint(
        action_type=action_type,
        target_repository_owner=target_repository_owner,
        target_repository_name=target_repository_name,
        title=payload.title,
        body=payload.body,
    )


def create_action_proposal(
    *,
    action_proposal_id: UUID = PROPOSAL_ID,
    technical_debt_id: UUID = TECHNICAL_DEBT_ID,
    action_type: ActionType = ActionType.CREATE_GITHUB_ISSUE,
    target_repository_owner: str = "tdi-demo-target",
    target_repository_name: str = "tdi-action-preview",
    payload: GitHubIssuePayload | None = None,
    payload_fingerprint: str | None = None,
    reconciliation_marker: str | None = None,
    prepared_by: str = "poc:local-reviewer",
    created_at: datetime | None = None,
) -> ActionProposal:
    resolved_payload = payload if payload is not None else _payload(
        action_proposal_id=action_proposal_id
    )
    return ActionProposal(
        action_proposal_id=action_proposal_id,
        technical_debt_id=technical_debt_id,
        action_type=action_type,
        target_repository_owner=target_repository_owner,
        target_repository_name=target_repository_name,
        payload=resolved_payload,
        payload_fingerprint=(
            payload_fingerprint
            if payload_fingerprint is not None
            else _fingerprint(
                resolved_payload,
                target_repository_owner=target_repository_owner,
                target_repository_name=target_repository_name,
            )
        ),
        reconciliation_marker=(
            reconciliation_marker
            if reconciliation_marker is not None
            else action_proposal_reconciliation_marker(action_proposal_id)
        ),
        prepared_by=prepared_by,
        created_at=CREATED_AT if created_at is None else created_at,
    )


def test_action_proposal_is_immutable() -> None:
    proposal = create_action_proposal()

    with pytest.raises(FrozenInstanceError):
        proposal.prepared_by = "poc:other-reviewer"  # type: ignore[misc]


def test_create_github_issue_is_the_only_supported_action_type() -> None:
    assert list(ActionType) == [ActionType.CREATE_GITHUB_ISSUE]
    assert ActionType.CREATE_GITHUB_ISSUE.value == "CREATE_GITHUB_ISSUE"

    with pytest.raises(ValueError, match="action type"):
        create_action_proposal(action_type="CREATE_PULL_REQUEST")  # type: ignore[arg-type]


def test_action_proposal_is_distinct_from_candidate_decision_and_debt() -> None:
    proposal = create_action_proposal()

    assert not isinstance(proposal, Candidate)
    assert not isinstance(proposal, HumanDecision)
    assert not isinstance(proposal, TechnicalDebt)
    assert proposal.action_proposal_id != proposal.technical_debt_id
    assert not hasattr(proposal, "status")
    assert not hasattr(proposal, "approved")
    assert not hasattr(proposal, "executed")
    assert not hasattr(proposal, "verified")
    assert not hasattr(proposal, "risk")
    assert not hasattr(proposal, "effort")
    assert not hasattr(proposal, "owner")


def test_reconciliation_marker_is_derived_from_proposal_identity() -> None:
    proposal = create_action_proposal()

    assert proposal.reconciliation_marker == f"tdiq-action-proposal:{PROPOSAL_ID}"
    assert proposal.reconciliation_marker in proposal.payload.body


def test_reconciliation_marker_must_match_proposal_identity() -> None:
    payload = _payload()
    with pytest.raises(ValueError, match="reconciliation marker"):
        create_action_proposal(
            payload=payload,
            payload_fingerprint=_fingerprint(payload),
            reconciliation_marker="tdiq-action-proposal:other",
        )


def test_body_must_include_the_reconciliation_marker() -> None:
    payload = GitHubIssuePayload(title="Technical debt: asset", body="No marker here")
    with pytest.raises(ValueError, match="must include the reconciliation marker"):
        create_action_proposal(
            payload=payload,
            payload_fingerprint=_fingerprint(payload),
        )


def test_fingerprint_is_deterministic_for_the_same_canonical_input() -> None:
    payload = _payload()
    first = _fingerprint(payload)
    second = _fingerprint(payload)

    assert first == second
    assert first == create_action_proposal().payload_fingerprint
    assert len(first) == 64


def test_fingerprint_uses_the_final_body_including_the_marker() -> None:
    marker = action_proposal_reconciliation_marker(PROPOSAL_ID)
    without_marker = canonical_action_payload_fingerprint(
        action_type=ActionType.CREATE_GITHUB_ISSUE.value,
        target_repository_owner="tdi-demo-target",
        target_repository_name="tdi-action-preview",
        title="Technical debt: repo-borealis-renderer",
        body="Technical debt remediation tracking issue\n\n",
    )
    with_marker = canonical_action_payload_fingerprint(
        action_type=ActionType.CREATE_GITHUB_ISSUE.value,
        target_repository_owner="tdi-demo-target",
        target_repository_name="tdi-action-preview",
        title="Technical debt: repo-borealis-renderer",
        body=f"Technical debt remediation tracking issue\n\n{marker}\n",
    )

    assert without_marker != with_marker
    assert with_marker == create_action_proposal().payload_fingerprint


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("target_repository_owner", "other-owner"),
        ("target_repository_name", "other-repo"),
        ("title", "Changed title"),
        ("body", "Changed body\n"),
        ("action_type", "CREATE_PULL_REQUEST"),
    ),
)
def test_fingerprint_changes_when_canonical_input_changes(
    field_name: str,
    value: str,
) -> None:
    payload = _payload()
    baseline = _fingerprint(payload)
    changed = canonical_action_payload_fingerprint(
        action_type=(
            value
            if field_name == "action_type"
            else ActionType.CREATE_GITHUB_ISSUE.value
        ),
        target_repository_owner=(
            value if field_name == "target_repository_owner" else "tdi-demo-target"
        ),
        target_repository_name=(
            value if field_name == "target_repository_name" else "tdi-action-preview"
        ),
        title=value if field_name == "title" else payload.title,
        body=(
            f"{value}{action_proposal_reconciliation_marker(PROPOSAL_ID)}\n"
            if field_name == "body"
            else payload.body
        ),
    )

    assert changed != baseline


def test_fingerprint_does_not_bind_actor_or_timestamp() -> None:
    first = create_action_proposal(prepared_by="poc:reviewer-a")
    second = create_action_proposal(
        prepared_by="poc:reviewer-b",
        created_at=datetime(2026, 9, 8, 9, 0, tzinfo=UTC),
    )

    assert first.payload_fingerprint == second.payload_fingerprint


def test_action_proposal_requires_timezone_aware_created_at() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        create_action_proposal(created_at=datetime(2026, 9, 7, 14, 0))


def test_mismatched_fingerprint_is_rejected() -> None:
    with pytest.raises(ValueError, match="fingerprint"):
        create_action_proposal(payload_fingerprint="0" * 64)
