from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class HumanDecisionType(StrEnum):
    VALIDATE = "VALIDATE"
    REJECT = "REJECT"
    REQUEST_INFO = "REQUEST_INFO"


def has_meaningful_text(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def human_decision_content_violation(
    decision_type: HumanDecisionType,
    rationale: str | None,
    requested_information: str | None,
) -> str | None:
    """Return a content-rule violation, or None when the decision payload is valid."""
    if decision_type in {HumanDecisionType.VALIDATE, HumanDecisionType.REJECT}:
        if not has_meaningful_text(rationale):
            return f"{decision_type} requires a nonblank rationale"
        if has_meaningful_text(requested_information):
            return f"{decision_type} must not include requested information"
        return None

    if decision_type is HumanDecisionType.REQUEST_INFO:
        if not has_meaningful_text(requested_information):
            return "REQUEST_INFO requires nonblank requested information"
        return None

    return "Human decision type must be supported"


@dataclass(frozen=True)
class HumanDecision:
    """Immutable human governance decision for one Candidate."""

    human_decision_id: UUID
    candidate_id: UUID
    sequence_number: int
    decision_type: HumanDecisionType
    rationale: str | None
    requested_information: str | None
    actor_reference: str
    created_at: datetime

    def __post_init__(self) -> None:
        if self.sequence_number < 1:
            raise ValueError("HumanDecision sequence number must be >= 1")
        if not isinstance(self.decision_type, HumanDecisionType):
            raise ValueError("HumanDecision type must be supported")
        if not self.actor_reference.strip():
            raise ValueError("HumanDecision actor reference must not be blank")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("HumanDecision created timestamp must be timezone-aware")

        violation = human_decision_content_violation(
            self.decision_type,
            self.rationale,
            self.requested_information,
        )
        if violation is not None:
            raise ValueError(violation)
