from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from app.actions.contracts import (
    ApproveActionProposalCommand,
    PrepareActionProposalCommand,
)


def test_approve_command_only_carries_identity_and_expected_fingerprint() -> None:
    technical_debt_id = uuid4()
    action_proposal_id = uuid4()
    fingerprint = "b" * 64
    command = ApproveActionProposalCommand(
        technical_debt_id=technical_debt_id,
        action_proposal_id=action_proposal_id,
        expected_payload_fingerprint=fingerprint,
    )

    fields = ApproveActionProposalCommand.__dataclass_fields__
    assert command.technical_debt_id == technical_debt_id
    assert command.action_proposal_id == action_proposal_id
    assert command.expected_payload_fingerprint == fingerprint
    assert set(fields) == {
        "technical_debt_id",
        "action_proposal_id",
        "expected_payload_fingerprint",
    }
    for forbidden in (
        "actor_reference",
        "approved",
        "repository",
        "title",
        "body",
        "action_type",
        "effect",
        "risk",
        "scope",
        "policy",
        "execution",
    ):
        assert forbidden not in fields


def test_approve_command_is_immutable() -> None:
    command = ApproveActionProposalCommand(
        technical_debt_id=uuid4(),
        action_proposal_id=uuid4(),
        expected_payload_fingerprint="c" * 64,
    )

    with pytest.raises(FrozenInstanceError):
        command.expected_payload_fingerprint = "d" * 64  # type: ignore[misc]


def test_approve_command_rejects_non_canonical_fingerprint() -> None:
    with pytest.raises(ValueError, match="fingerprint"):
        ApproveActionProposalCommand(
            technical_debt_id=uuid4(),
            action_proposal_id=uuid4(),
            expected_payload_fingerprint="not-hex",
        )


def test_approve_command_is_distinct_from_prepare_command() -> None:
    assert (
        set(ApproveActionProposalCommand.__dataclass_fields__)
        != set(PrepareActionProposalCommand.__dataclass_fields__)
    )
