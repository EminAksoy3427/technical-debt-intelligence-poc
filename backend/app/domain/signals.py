from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Evidence:
    evidence_id: UUID
    source_system: str
    source_reference: str
    captured_at: datetime
    reference_uri: str | None = None

    def __post_init__(self) -> None:
        if not self.source_system.strip():
            raise ValueError("Evidence source system must not be blank")
        if not self.source_reference.strip():
            raise ValueError("Evidence source reference must not be blank")
        if self.captured_at.tzinfo is None or self.captured_at.utcoffset() is None:
            raise ValueError("Evidence captured timestamp must be timezone-aware")


@dataclass(frozen=True)
class Signal:
    signal_id: UUID
    source_system: str
    source_record_id: str
    detected_at: datetime
    signal_type: str
    severity: str | None = None
    asset_hint: str | None = None
    evidence_ids: frozenset[UUID] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.source_system.strip():
            raise ValueError("Signal source system must not be blank")
        if not self.source_record_id.strip():
            raise ValueError("Signal source record identifier must not be blank")
        if not self.signal_type.strip():
            raise ValueError("Signal type must not be blank")
        if self.detected_at.tzinfo is None or self.detected_at.utcoffset() is None:
            raise ValueError("Signal detection timestamp must be timezone-aware")

        object.__setattr__(self, "evidence_ids", frozenset(self.evidence_ids))
