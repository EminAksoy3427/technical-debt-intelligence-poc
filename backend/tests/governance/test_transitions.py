from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.domain.human_decisions import HumanDecision, HumanDecisionType
from app.governance.contracts import (
    CandidateGovernanceState,
    InvalidGovernanceHistory,
    InvalidGovernanceTransition,
)
from app.governance.transitions import (
    derive_candidate_governance,
    next_governance_state,
)

CREATED_AT = datetime(2026, 9, 6, 16, 10, tzinfo=UTC)
CANDIDATE_ID = UUID("10000000-0000-0000-0000-000000000001")


def create_decision(
    decision_type: HumanDecisionType,
    sequence_number: int,
    *,
    candidate_id: UUID = CANDIDATE_ID,
) -> HumanDecision:
    if decision_type is HumanDecisionType.REQUEST_INFO:
        rationale = None
        requested_information = "Need the owning team."
    else:
        rationale = "A human governance decision."
        requested_information = None

    return HumanDecision(
        human_decision_id=uuid4(),
        candidate_id=candidate_id,
        sequence_number=sequence_number,
        decision_type=decision_type,
        rationale=rationale,
        requested_information=requested_information,
        actor_reference="poc:local-reviewer",
        created_at=CREATED_AT,
    )


@pytest.mark.parametrize(
    ("current", "decision", "expected"),
    [
        (
            CandidateGovernanceState.PENDING,
            HumanDecisionType.VALIDATE,
            CandidateGovernanceState.VALIDATED,
        ),
        (
            CandidateGovernanceState.PENDING,
            HumanDecisionType.REJECT,
            CandidateGovernanceState.REJECTED,
        ),
        (
            CandidateGovernanceState.PENDING,
            HumanDecisionType.REQUEST_INFO,
            CandidateGovernanceState.INFORMATION_REQUESTED,
        ),
        (
            CandidateGovernanceState.INFORMATION_REQUESTED,
            HumanDecisionType.VALIDATE,
            CandidateGovernanceState.VALIDATED,
        ),
        (
            CandidateGovernanceState.INFORMATION_REQUESTED,
            HumanDecisionType.REJECT,
            CandidateGovernanceState.REJECTED,
        ),
        (
            CandidateGovernanceState.INFORMATION_REQUESTED,
            HumanDecisionType.REQUEST_INFO,
            CandidateGovernanceState.INFORMATION_REQUESTED,
        ),
    ],
)
def test_legal_governance_transitions(
    current: CandidateGovernanceState,
    decision: HumanDecisionType,
    expected: CandidateGovernanceState,
) -> None:
    assert next_governance_state(current, decision) is expected


@pytest.mark.parametrize(
    "terminal_state",
    [CandidateGovernanceState.VALIDATED, CandidateGovernanceState.REJECTED],
)
@pytest.mark.parametrize("decision", list(HumanDecisionType))
def test_terminal_states_reject_every_decision(
    terminal_state: CandidateGovernanceState,
    decision: HumanDecisionType,
) -> None:
    with pytest.raises(InvalidGovernanceTransition, match="not a legal transition"):
        next_governance_state(terminal_state, decision)


def test_empty_history_is_pending_revision_zero() -> None:
    snapshot = derive_candidate_governance(())

    assert snapshot.state is CandidateGovernanceState.PENDING
    assert snapshot.revision == 0


def test_first_decision_gives_revision_one() -> None:
    snapshot = derive_candidate_governance(
        (create_decision(HumanDecisionType.VALIDATE, 1),)
    )

    assert snapshot.state is CandidateGovernanceState.VALIDATED
    assert snapshot.revision == 1


def test_multiple_request_info_decisions_increment_revision() -> None:
    snapshot = derive_candidate_governance(
        (
            create_decision(HumanDecisionType.REQUEST_INFO, 1),
            create_decision(HumanDecisionType.REQUEST_INFO, 2),
        )
    )

    assert snapshot.state is CandidateGovernanceState.INFORMATION_REQUESTED
    assert snapshot.revision == 2


def test_request_info_then_validate_is_validated() -> None:
    snapshot = derive_candidate_governance(
        (
            create_decision(HumanDecisionType.REQUEST_INFO, 1),
            create_decision(HumanDecisionType.VALIDATE, 2),
        )
    )

    assert snapshot.state is CandidateGovernanceState.VALIDATED
    assert snapshot.revision == 2


def test_request_info_then_reject_is_rejected() -> None:
    snapshot = derive_candidate_governance(
        (
            create_decision(HumanDecisionType.REQUEST_INFO, 1),
            create_decision(HumanDecisionType.REJECT, 2),
        )
    )

    assert snapshot.state is CandidateGovernanceState.REJECTED
    assert snapshot.revision == 2


def test_non_contiguous_sequence_is_rejected() -> None:
    with pytest.raises(InvalidGovernanceHistory, match="contiguous"):
        derive_candidate_governance(
            (
                create_decision(HumanDecisionType.REQUEST_INFO, 1),
                create_decision(HumanDecisionType.VALIDATE, 3),
            )
        )


def test_duplicate_sequence_is_rejected() -> None:
    with pytest.raises(InvalidGovernanceHistory, match="duplicate"):
        derive_candidate_governance(
            (
                create_decision(HumanDecisionType.REQUEST_INFO, 1),
                create_decision(HumanDecisionType.VALIDATE, 1),
            )
        )


def test_history_must_begin_at_sequence_one() -> None:
    with pytest.raises(InvalidGovernanceHistory, match="begin at 1"):
        derive_candidate_governance(
            (create_decision(HumanDecisionType.VALIDATE, 2),)
        )


@pytest.mark.parametrize(
    "terminal_decision",
    [HumanDecisionType.VALIDATE, HumanDecisionType.REJECT],
)
@pytest.mark.parametrize("follow_on", list(HumanDecisionType))
def test_decision_after_terminal_history_is_rejected(
    terminal_decision: HumanDecisionType,
    follow_on: HumanDecisionType,
) -> None:
    with pytest.raises(InvalidGovernanceHistory, match="not a legal transition"):
        derive_candidate_governance(
            (
                create_decision(terminal_decision, 1),
                create_decision(follow_on, 2),
            )
        )


def test_history_must_belong_to_one_candidate() -> None:
    with pytest.raises(InvalidGovernanceHistory, match="one Candidate"):
        derive_candidate_governance(
            (
                create_decision(HumanDecisionType.REQUEST_INFO, 1),
                create_decision(
                    HumanDecisionType.VALIDATE,
                    2,
                    candidate_id=uuid4(),
                ),
            )
        )
