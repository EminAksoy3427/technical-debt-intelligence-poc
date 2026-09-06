from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.domain.candidates import Candidate
from app.domain.human_decisions import HumanDecision, HumanDecisionType
from app.domain.technical_debts import TechnicalDebt

CREATED_AT = datetime(2026, 9, 6, 16, 0, tzinfo=UTC)
CANDIDATE_ID = UUID("10000000-0000-0000-0000-000000000001")


def create_human_decision(
    *,
    decision_type: HumanDecisionType = HumanDecisionType.VALIDATE,
    sequence_number: int = 1,
    rationale: str | None = "The Candidate is a validated structural issue.",
    requested_information: str | None = None,
    actor_reference: str = "poc:local-reviewer",
    created_at: datetime | None = None,
) -> HumanDecision:
    if (
        decision_type is HumanDecisionType.REQUEST_INFO
        and requested_information is None
    ):
        requested_information = "Which service owns the failing dependency?"
        if rationale == "The Candidate is a validated structural issue.":
            rationale = None

    return HumanDecision(
        human_decision_id=uuid4(),
        candidate_id=CANDIDATE_ID,
        sequence_number=sequence_number,
        decision_type=decision_type,
        rationale=rationale,
        requested_information=requested_information,
        actor_reference=actor_reference,
        created_at=CREATED_AT if created_at is None else created_at,
    )


def test_validate_accepts_nonblank_rationale() -> None:
    decision = create_human_decision(decision_type=HumanDecisionType.VALIDATE)

    assert decision.decision_type is HumanDecisionType.VALIDATE
    assert decision.sequence_number == 1
    assert decision.rationale is not None
    assert decision.requested_information is None


def test_reject_accepts_nonblank_rationale() -> None:
    decision = create_human_decision(
        decision_type=HumanDecisionType.REJECT,
        rationale="The findings do not form a structural issue.",
    )

    assert decision.decision_type is HumanDecisionType.REJECT
    assert decision.rationale is not None


def test_request_info_accepts_nonblank_requested_information() -> None:
    decision = create_human_decision(
        decision_type=HumanDecisionType.REQUEST_INFO,
        rationale=None,
        requested_information="Need the owning team for payments-api.",
    )

    assert decision.decision_type is HumanDecisionType.REQUEST_INFO
    assert decision.requested_information is not None


@pytest.mark.parametrize("rationale", [None, "", "  ", "\t"])
@pytest.mark.parametrize(
    "decision_type",
    [HumanDecisionType.VALIDATE, HumanDecisionType.REJECT],
)
def test_validate_and_reject_require_nonblank_rationale(
    decision_type: HumanDecisionType,
    rationale: str | None,
) -> None:
    with pytest.raises(ValueError, match="nonblank rationale"):
        create_human_decision(decision_type=decision_type, rationale=rationale)


@pytest.mark.parametrize("requested_information", [None, "", "  "])
def test_request_info_requires_nonblank_requested_information(
    requested_information: str | None,
) -> None:
    with pytest.raises(ValueError, match="requested information"):
        HumanDecision(
            human_decision_id=uuid4(),
            candidate_id=CANDIDATE_ID,
            sequence_number=1,
            decision_type=HumanDecisionType.REQUEST_INFO,
            rationale=None,
            requested_information=requested_information,
            actor_reference="poc:local-reviewer",
            created_at=CREATED_AT,
        )


@pytest.mark.parametrize(
    "decision_type",
    [HumanDecisionType.VALIDATE, HumanDecisionType.REJECT],
)
def test_validate_and_reject_reject_requested_information(
    decision_type: HumanDecisionType,
) -> None:
    with pytest.raises(ValueError, match="must not include requested information"):
        create_human_decision(
            decision_type=decision_type,
            requested_information="Please explain the blast radius.",
        )


def test_human_decision_is_immutable() -> None:
    decision = create_human_decision()

    with pytest.raises(FrozenInstanceError):
        decision.rationale = "changed"  # type: ignore[misc]


def test_human_decision_requires_timezone_aware_created_at() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        create_human_decision(created_at=datetime(2026, 9, 6, 16, 0))


def test_human_decision_requires_sequence_number_at_least_one() -> None:
    with pytest.raises(ValueError, match="sequence number"):
        create_human_decision(sequence_number=0)


def test_human_decision_requires_nonblank_actor_reference() -> None:
    with pytest.raises(ValueError, match="actor reference"):
        create_human_decision(actor_reference="  ")


def test_human_decision_does_not_carry_technical_debt_identity() -> None:
    decision = create_human_decision()

    assert not hasattr(decision, "resulting_technical_debt_id")
    assert not hasattr(decision, "technical_debt_id")
    assert not isinstance(decision, Candidate)
    assert not isinstance(decision, TechnicalDebt)
