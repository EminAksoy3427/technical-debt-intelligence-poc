from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.domain.action_approvals import ActionApproval
from app.domain.action_proposals import ActionProposal
from app.domain.human_decisions import HumanDecision
from app.domain.technical_debts import TechnicalDebt

CREATED_AT = datetime(2026, 9, 7, 17, 0, tzinfo=UTC)
APPROVAL_ID = UUID("00000000-0000-0000-0000-000000000601")
PROPOSAL_ID = UUID("00000000-0000-0000-0000-000000000501")
FINGERPRINT = "a" * 64


def create_action_approval(
    *,
    action_approval_id: UUID = APPROVAL_ID,
    action_proposal_id: UUID = PROPOSAL_ID,
    payload_fingerprint: str = FINGERPRINT,
    actor_reference: str = "poc:local-reviewer",
    created_at: datetime | None = None,
) -> ActionApproval:
    return ActionApproval(
        action_approval_id=action_approval_id,
        action_proposal_id=action_proposal_id,
        payload_fingerprint=payload_fingerprint,
        actor_reference=actor_reference,
        created_at=CREATED_AT if created_at is None else created_at,
    )


def test_action_approval_is_immutable() -> None:
    approval = create_action_approval()

    with pytest.raises(FrozenInstanceError):
        approval.actor_reference = "poc:other-reviewer"  # type: ignore[misc]


def test_action_approval_is_distinct_from_proposal_decision_and_debt() -> None:
    approval = create_action_approval()

    assert not isinstance(approval, ActionProposal)
    assert not isinstance(approval, HumanDecision)
    assert not isinstance(approval, TechnicalDebt)
    assert approval.action_approval_id != approval.action_proposal_id
    assert set(ActionApproval.__dataclass_fields__) == {
        "action_approval_id",
        "action_proposal_id",
        "payload_fingerprint",
        "actor_reference",
        "created_at",
    }
    assert not hasattr(approval, "approved")
    assert not hasattr(approval, "status")
    assert not hasattr(approval, "revoked")
    assert not hasattr(approval, "rejected")
    assert not hasattr(approval, "role")
    assert not hasattr(approval, "risk")
    assert not hasattr(approval, "effort")
    assert not hasattr(approval, "priority")
    assert not hasattr(approval, "title")
    assert not hasattr(approval, "body")
    assert not hasattr(approval, "repository")


def test_action_approval_requires_timezone_aware_created_at() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        create_action_approval(created_at=datetime(2026, 9, 7, 17, 0))


def test_action_approval_requires_canonical_fingerprint() -> None:
    with pytest.raises(ValueError, match="fingerprint"):
        create_action_approval(payload_fingerprint="not-a-fingerprint")
    with pytest.raises(ValueError, match="fingerprint"):
        create_action_approval(payload_fingerprint="A" * 64)


def test_action_approval_requires_nonblank_actor() -> None:
    with pytest.raises(ValueError, match="actor"):
        create_action_approval(actor_reference="   ")
