from dataclasses import dataclass
from uuid import UUID

from app.domain.assets import CanonicalAssetRef


@dataclass(frozen=True)
class Candidate:
    candidate_id: UUID
    signal_ids: frozenset[UUID]
    evidence_ids: frozenset[UUID]
    canonical_asset: CanonicalAssetRef
    hypothesis: str
    correlation_rationale: str

    def __post_init__(self) -> None:
        signal_ids = frozenset(self.signal_ids)
        evidence_ids = frozenset(self.evidence_ids)

        if not signal_ids:
            raise ValueError("Candidate must reference at least one Signal")
        if not evidence_ids:
            raise ValueError("Candidate must reference at least one Evidence item")
        if not self.hypothesis.strip():
            raise ValueError("Candidate hypothesis must not be blank")
        if not self.correlation_rationale.strip():
            raise ValueError("Candidate correlation rationale must not be blank")
        if not isinstance(self.canonical_asset, CanonicalAssetRef):
            raise ValueError("Candidate must have a valid canonical asset reference")

        object.__setattr__(self, "signal_ids", signal_ids)
        object.__setattr__(self, "evidence_ids", evidence_ids)
