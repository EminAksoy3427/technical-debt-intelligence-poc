from dataclasses import FrozenInstanceError
from uuid import UUID, uuid4

import pytest

from app.domain.human_decisions import HumanDecisionType
from app.governance.contracts import (
    HumanActorContext,
    HumanValidationCommand,
    InvalidHumanDecisionCommand,
    StaleGovernanceRevision,
)
from app.governance.transitions import require_expected_governance_revision

CANDIDATE_ID = UUID("10000000-0000-0000-0000-000000000001")


def create_command(
    *,
    decision: HumanDecisionType = HumanDecisionType.VALIDATE,
    expected_governance_revision: int = 0,
    rationale: str | None = "The Candidate is a validated structural issue.",
    requested_information: str | None = None,
) -> HumanValidationCommand:
    return HumanValidationCommand(
        candidate_id=CANDIDATE_ID,
        decision=decision,
        expected_governance_revision=expected_governance_revision,
        rationale=rationale,
        requested_information=requested_information,
    )


def test_validate_command_accepts_nonblank_rationale() -> None:
    command = create_command(decision=HumanDecisionType.VALIDATE)

    assert command.decision is HumanDecisionType.VALIDATE
    assert command.rationale == "The Candidate is a validated structural issue."
    assert command.requested_information is None
    assert command.expected_governance_revision == 0


def test_reject_command_accepts_nonblank_rationale() -> None:
    command = create_command(
        decision=HumanDecisionType.REJECT,
        rationale="Not a structural issue.",
    )

    assert command.decision is HumanDecisionType.REJECT
    assert command.rationale == "Not a structural issue."
    assert command.requested_information is None


def test_request_info_command_accepts_nonblank_requested_information() -> None:
    command = create_command(
        decision=HumanDecisionType.REQUEST_INFO,
        rationale=None,
        requested_information="Who owns payments-api?",
    )

    assert command.decision is HumanDecisionType.REQUEST_INFO
    assert command.requested_information == "Who owns payments-api?"
    assert command.rationale is None


@pytest.mark.parametrize("rationale", [None, "", "  ", "\t"])
@pytest.mark.parametrize(
    "decision",
    [HumanDecisionType.VALIDATE, HumanDecisionType.REJECT],
)
def test_validate_and_reject_commands_require_nonblank_rationale(
    decision: HumanDecisionType,
    rationale: str | None,
) -> None:
    with pytest.raises(InvalidHumanDecisionCommand, match="nonblank rationale"):
        create_command(decision=decision, rationale=rationale)


@pytest.mark.parametrize("requested_information", [None, "", "   "])
def test_request_info_command_requires_nonblank_requested_information(
    requested_information: str | None,
) -> None:
    with pytest.raises(InvalidHumanDecisionCommand, match="requested information"):
        create_command(
            decision=HumanDecisionType.REQUEST_INFO,
            rationale=None,
            requested_information=requested_information,
        )


@pytest.mark.parametrize(
    "decision",
    [HumanDecisionType.VALIDATE, HumanDecisionType.REJECT],
)
def test_validate_and_reject_commands_reject_requested_information(
    decision: HumanDecisionType,
) -> None:
    with pytest.raises(
        InvalidHumanDecisionCommand,
        match="must not include requested information",
    ):
        create_command(
            decision=decision,
            requested_information="Need more evidence first.",
        )


def test_command_trims_blank_optional_requested_information_for_validate() -> None:
    command = create_command(
        decision=HumanDecisionType.VALIDATE,
        requested_information="   ",
    )

    assert command.requested_information is None


def test_command_trims_blank_optional_rationale_for_request_info() -> None:
    command = create_command(
        decision=HumanDecisionType.REQUEST_INFO,
        rationale="  ",
        requested_information="  Confirm the owning team.  ",
    )

    assert command.rationale is None
    assert command.requested_information == "Confirm the owning team."


def test_command_rejects_negative_expected_revision() -> None:
    with pytest.raises(
        InvalidHumanDecisionCommand, match="expected_governance_revision"
    ):
        create_command(expected_governance_revision=-1)


def test_command_rejects_unsupported_decision() -> None:
    with pytest.raises(InvalidHumanDecisionCommand, match="decision must be supported"):
        create_command(decision="MERGE")  # type: ignore[arg-type]


def test_command_does_not_accept_actor_or_authority_fields() -> None:
    fields = HumanValidationCommand.__dataclass_fields__

    assert "actor_reference" not in fields
    assert "role" not in fields
    assert "authorization" not in fields
    assert "approval" not in fields
    assert "timestamp" not in fields
    assert "technical_debt_id" not in fields
    with pytest.raises(TypeError):
        HumanValidationCommand(
            candidate_id=CANDIDATE_ID,
            decision=HumanDecisionType.VALIDATE,
            expected_governance_revision=0,
            rationale="Valid.",
            actor_reference="poc:local-reviewer",
        )


def test_human_actor_context_is_server_owned_opaque_reference() -> None:
    actor = HumanActorContext(actor_reference="poc:local-reviewer")

    assert actor.actor_reference == "poc:local-reviewer"
    assert HumanActorContext.__dataclass_fields__.keys() == {"actor_reference"}
    with pytest.raises(ValueError, match="actor reference"):
        HumanActorContext(actor_reference=" ")
    with pytest.raises(FrozenInstanceError):
        actor.actor_reference = "other"  # type: ignore[misc]
    with pytest.raises(TypeError):
        HumanActorContext(
            actor_reference="poc:local-reviewer",
            role="reviewer",
        )


def test_stale_governance_revision_is_a_pure_mismatch_check() -> None:
    require_expected_governance_revision(0, 0)
    require_expected_governance_revision(2, 2)

    with pytest.raises(StaleGovernanceRevision, match="does not match"):
        require_expected_governance_revision(1, 0)


def test_command_candidate_identity_is_explicit() -> None:
    other_id = uuid4()
    command = HumanValidationCommand(
        candidate_id=other_id,
        decision=HumanDecisionType.VALIDATE,
        expected_governance_revision=0,
        rationale="Valid.",
    )

    assert command.candidate_id == other_id
