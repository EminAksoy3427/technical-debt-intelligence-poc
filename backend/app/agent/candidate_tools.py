from typing import Final
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict

from app.agent.contracts import (
    CandidateToolInput,
    ToolDescriptor,
    ToolEffect,
    ToolRegistration,
    ToolRisk,
)
from app.agent.ports import CandidateInvestigationReader
from app.domain.enterprise_estate import AssetType


class ReadCandidateEvidenceInput(CandidateToolInput):
    candidate_id: UUID


class _ImmutableToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CandidateAssetResult(_ImmutableToolResult):
    asset_key: str
    asset_type: AssetType


class CandidateSignalResult(_ImmutableToolResult):
    signal_id: UUID
    source_system: str
    source_record_id: str
    detected_at: AwareDatetime
    signal_type: str
    severity: str | None
    evidence_ids: tuple[UUID, ...]


class CandidateEvidenceResult(_ImmutableToolResult):
    evidence_id: UUID
    source_system: str
    source_reference: str
    captured_at: AwareDatetime
    reference_uri: str | None


class ReadCandidateEvidenceResult(_ImmutableToolResult):
    candidate_id: UUID
    canonical_asset: CandidateAssetResult
    hypothesis: str
    correlation_rationale: str
    signals: tuple[CandidateSignalResult, ...]
    evidence: tuple[CandidateEvidenceResult, ...]


class CandidateEvidenceNotFoundError(LookupError):
    """The requested Candidate has no investigation read model."""


READ_CANDIDATE_EVIDENCE_DESCRIPTOR: Final = ToolDescriptor(
    tool_id="read_candidate_evidence",
    version="1.0.0",
    description="Read grounded Signal and Evidence facts for one Candidate.",
    effect=ToolEffect.READ,
    risk=ToolRisk.LOW,
    required_scopes=frozenset({"candidate:read"}),
)


def create_read_candidate_evidence_registration(
    reader: CandidateInvestigationReader,
) -> ToolRegistration[ReadCandidateEvidenceInput, ReadCandidateEvidenceResult]:
    def read_candidate_evidence(
        tool_input: ReadCandidateEvidenceInput,
    ) -> ReadCandidateEvidenceResult:
        investigation = reader.read_candidate_evidence(tool_input.candidate_id)
        if investigation is None:
            raise CandidateEvidenceNotFoundError(
                f"Candidate not found: {tool_input.candidate_id}"
            )

        return ReadCandidateEvidenceResult(
            candidate_id=investigation.candidate_id,
            canonical_asset=CandidateAssetResult(
                asset_key=investigation.asset_key,
                asset_type=investigation.asset_type,
            ),
            hypothesis=investigation.hypothesis,
            correlation_rationale=investigation.correlation_rationale,
            signals=tuple(
                CandidateSignalResult(
                    signal_id=signal.signal_id,
                    source_system=signal.source_system,
                    source_record_id=signal.source_record_id,
                    detected_at=signal.detected_at,
                    signal_type=signal.signal_type,
                    severity=signal.severity,
                    evidence_ids=signal.evidence_ids,
                )
                for signal in investigation.signals
            ),
            evidence=tuple(
                CandidateEvidenceResult(
                    evidence_id=evidence.evidence_id,
                    source_system=evidence.source_system,
                    source_reference=evidence.source_reference,
                    captured_at=evidence.captured_at,
                    reference_uri=evidence.reference_uri,
                )
                for evidence in investigation.evidence
            ),
        )

    return ToolRegistration(
        descriptor=READ_CANDIDATE_EVIDENCE_DESCRIPTOR,
        input_model=ReadCandidateEvidenceInput,
        result_model=ReadCandidateEvidenceResult,
        executor=read_candidate_evidence,
    )
