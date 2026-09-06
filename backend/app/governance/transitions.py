from collections.abc import Sequence
from types import MappingProxyType

from app.domain.human_decisions import HumanDecision, HumanDecisionType
from app.governance.contracts import (
    CandidateGovernanceSnapshot,
    CandidateGovernanceState,
    InvalidGovernanceHistory,
    InvalidGovernanceTransition,
    StaleGovernanceRevision,
)

_TRANSITIONS = MappingProxyType(
    {
        (
            CandidateGovernanceState.PENDING,
            HumanDecisionType.VALIDATE,
        ): CandidateGovernanceState.VALIDATED,
        (
            CandidateGovernanceState.PENDING,
            HumanDecisionType.REJECT,
        ): CandidateGovernanceState.REJECTED,
        (
            CandidateGovernanceState.PENDING,
            HumanDecisionType.REQUEST_INFO,
        ): CandidateGovernanceState.INFORMATION_REQUESTED,
        (
            CandidateGovernanceState.INFORMATION_REQUESTED,
            HumanDecisionType.VALIDATE,
        ): CandidateGovernanceState.VALIDATED,
        (
            CandidateGovernanceState.INFORMATION_REQUESTED,
            HumanDecisionType.REJECT,
        ): CandidateGovernanceState.REJECTED,
        (
            CandidateGovernanceState.INFORMATION_REQUESTED,
            HumanDecisionType.REQUEST_INFO,
        ): CandidateGovernanceState.INFORMATION_REQUESTED,
    }
)


def next_governance_state(
    current_state: CandidateGovernanceState,
    decision_type: HumanDecisionType,
) -> CandidateGovernanceState:
    """Return the next legal governance state, or raise for an invalid transition."""
    if not isinstance(current_state, CandidateGovernanceState):
        raise InvalidGovernanceTransition(
            "Candidate governance state must be supported"
        )
    if not isinstance(decision_type, HumanDecisionType):
        raise InvalidGovernanceTransition("Human decision type must be supported")

    try:
        return _TRANSITIONS[(current_state, decision_type)]
    except KeyError:
        raise InvalidGovernanceTransition(
            f"{decision_type} is not a legal transition from {current_state}"
        ) from None


def derive_candidate_governance(
    history: Sequence[HumanDecision],
) -> CandidateGovernanceSnapshot:
    """Derive governance state and revision from an append-only decision history."""
    if not history:
        return CandidateGovernanceSnapshot(
            state=CandidateGovernanceState.PENDING,
            revision=0,
        )

    _require_structurally_valid_history(history)

    state = CandidateGovernanceState.PENDING
    for decision in history:
        try:
            state = next_governance_state(state, decision.decision_type)
        except InvalidGovernanceTransition as exc:
            raise InvalidGovernanceHistory(str(exc)) from exc

    return CandidateGovernanceSnapshot(
        state=state,
        revision=history[-1].sequence_number,
    )


def require_expected_governance_revision(
    current_revision: int,
    expected_governance_revision: int,
) -> None:
    """Pure revision-match check. Persistence concurrency is not implemented here."""
    if current_revision != expected_governance_revision:
        raise StaleGovernanceRevision(
            "expected_governance_revision does not match the current revision"
        )


def _require_structurally_valid_history(history: Sequence[HumanDecision]) -> None:
    candidate_ids = {decision.candidate_id for decision in history}
    if len(candidate_ids) != 1:
        raise InvalidGovernanceHistory(
            "HumanDecision history must belong to one Candidate"
        )

    sequence_numbers = tuple(decision.sequence_number for decision in history)
    expected = tuple(range(1, len(history) + 1))
    if sequence_numbers == expected:
        return

    if len(set(sequence_numbers)) != len(sequence_numbers):
        raise InvalidGovernanceHistory(
            "HumanDecision history must not contain duplicate sequence numbers"
        )
    raise InvalidGovernanceHistory(
        "HumanDecision history sequence numbers must be contiguous and begin at 1"
    )
