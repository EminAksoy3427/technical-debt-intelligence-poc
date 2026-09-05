from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.enterprise_estate import AssetType


@dataclass(frozen=True)
class CandidateInvestigationSignal:
    signal_id: UUID
    source_system: str
    source_record_id: str
    detected_at: datetime
    signal_type: str
    severity: str | None
    evidence_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class CandidateInvestigationEvidence:
    evidence_id: UUID
    source_system: str
    source_reference: str
    captured_at: datetime
    reference_uri: str | None


@dataclass(frozen=True)
class CandidateInvestigation:
    candidate_id: UUID
    asset_key: str
    asset_type: AssetType
    hypothesis: str
    correlation_rationale: str
    signals: tuple[CandidateInvestigationSignal, ...]
    evidence: tuple[CandidateInvestigationEvidence, ...]


class CandidateInvestigationReader(Protocol):
    """Application-owned read capability needed by Candidate Agent Tools."""

    def read_candidate_evidence(
        self,
        candidate_id: UUID,
    ) -> CandidateInvestigation | None: ...
