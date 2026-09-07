from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

_FINGERPRINT_LENGTH = 64
_HEX_DIGITS = frozenset("0123456789abcdef")


def is_canonical_payload_fingerprint(value: str) -> bool:
    """Return True when value is a lowercase SHA-256 hex digest."""
    return len(value) == _FINGERPRINT_LENGTH and all(
        character in _HEX_DIGITS for character in value
    )


@dataclass(frozen=True)
class ActionApproval:
    """Immutable L4 approval of one exact ActionProposal preview.

    Existence of this record is not policy ALLOW and is not execution.
    """

    action_approval_id: UUID
    action_proposal_id: UUID
    payload_fingerprint: str
    actor_reference: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not is_canonical_payload_fingerprint(self.payload_fingerprint):
            raise ValueError(
                "ActionApproval payload fingerprint must be a SHA-256 hex digest"
            )
        if not self.actor_reference.strip():
            raise ValueError("ActionApproval actor reference must not be blank")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("ActionApproval created timestamp must be timezone-aware")
