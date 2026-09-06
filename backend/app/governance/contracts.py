from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.domain.human_decisions import (
    HumanDecisionType,
    human_decision_content_violation,
)


class CandidateGovernanceState(StrEnum):
    PENDING = "PENDING"
    INFORMATION_REQUESTED = "INFORMATION_REQUESTED"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"


class InvalidHumanDecisionCommand(ValueError):
    """A Human Validation command failed deterministic content or shape rules."""


class InvalidGovernanceTransition(ValueError):
    """The requested HumanDecision is not legal from the current governance state."""


class InvalidGovernanceHistory(ValueError):
    """A HumanDecision history is structurally impossible to derive."""


class StaleGovernanceRevision(ValueError):
    """The command expected a different governance revision than the current one."""


class CandidateNotFound(ValueError):
    """The Human Validation command referenced a Candidate that does not exist."""


class GovernancePersistenceConflict(ValueError):
    """A governance write violated a durable uniqueness guarantee."""


@dataclass(frozen=True)
class HumanActorContext:
    """Server-owned opaque actor reference for one Human Validation act."""

    actor_reference: str

    def __post_init__(self) -> None:
        if not self.actor_reference.strip():
            raise ValueError("Human actor reference must not be blank")


@dataclass(frozen=True)
class HumanValidationCommand:
    """Untrusted Human Validation intent. Actor identity is not client-supplied."""

    candidate_id: UUID
    decision: HumanDecisionType
    expected_governance_revision: int
    rationale: str | None = None
    requested_information: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.decision, HumanDecisionType):
            raise InvalidHumanDecisionCommand(
                "Human Validation decision must be supported"
            )
        if self.expected_governance_revision < 0:
            raise InvalidHumanDecisionCommand(
                "expected_governance_revision must be >= 0"
            )

        rationale = _normalized_optional_text(self.rationale)
        requested_information = _normalized_optional_text(self.requested_information)
        object.__setattr__(self, "rationale", rationale)
        object.__setattr__(self, "requested_information", requested_information)

        violation = human_decision_content_violation(
            self.decision,
            rationale,
            requested_information,
        )
        if violation is not None:
            raise InvalidHumanDecisionCommand(violation)


@dataclass(frozen=True)
class CandidateGovernanceSnapshot:
    """Governance state and revision derived from HumanDecision history."""

    state: CandidateGovernanceState
    revision: int

    def __post_init__(self) -> None:
        if not isinstance(self.state, CandidateGovernanceState):
            raise ValueError("Candidate governance state must be supported")
        if self.revision < 0:
            raise ValueError("Candidate governance revision must be >= 0")


def _normalized_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
