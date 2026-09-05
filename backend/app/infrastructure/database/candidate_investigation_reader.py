from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.agent.ports import (
    CandidateInvestigation,
    CandidateInvestigationEvidence,
    CandidateInvestigationSignal,
)
from app.infrastructure.database.candidate_read_model import load_candidate_detail


@dataclass(frozen=True)
class DatabaseCandidateInvestigationReader:
    """Project the existing Candidate detail read into the application port."""

    session: Session

    def read_candidate_evidence(
        self,
        candidate_id: UUID,
    ) -> CandidateInvestigation | None:
        detail = load_candidate_detail(self.session, candidate_id)
        if detail is None:
            return None

        candidate = detail.candidate
        return CandidateInvestigation(
            candidate_id=candidate.candidate_id,
            asset_key=candidate.canonical_asset.asset_key,
            asset_type=candidate.canonical_asset.asset_type,
            hypothesis=candidate.hypothesis,
            correlation_rationale=candidate.correlation_rationale,
            signals=tuple(
                CandidateInvestigationSignal(
                    signal_id=signal.signal_id,
                    source_system=signal.source_system,
                    source_record_id=signal.source_record_id,
                    detected_at=signal.detected_at,
                    signal_type=signal.signal_type,
                    severity=signal.severity,
                    evidence_ids=tuple(
                        sorted(signal.evidence_ids, key=lambda item: item.hex)
                    ),
                )
                for signal in detail.signals
            ),
            evidence=tuple(
                CandidateInvestigationEvidence(
                    evidence_id=evidence.evidence_id,
                    source_system=evidence.source_system,
                    source_reference=evidence.source_reference,
                    captured_at=evidence.captured_at,
                    reference_uri=evidence.reference_uri,
                )
                for evidence in detail.evidence
            ),
        )
