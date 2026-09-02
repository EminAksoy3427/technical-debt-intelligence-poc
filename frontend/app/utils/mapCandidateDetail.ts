import type { CandidateDetailPresentation } from '../types/candidate'
import type {
  CandidateDetailResponse,
  EvidenceResponse,
  SignalResponse,
} from '../types/candidateApi'

export function toCandidateDetailPresentation(
  detail: CandidateDetailResponse,
): CandidateDetailPresentation {
  return {
    candidate: {
      candidateId: detail.candidate.candidate_id,
      hypothesis: detail.candidate.hypothesis,
      canonicalAssetKey: detail.candidate.canonical_asset.asset_key,
      canonicalAssetType: detail.candidate.canonical_asset.asset_type,
      assetDisplayName: detail.enterprise_context.enterprise_asset.name,
      correlationRationale: detail.candidate.correlation_rationale,
    },
    signals: detail.signals.map(toCandidateSignalItem),
    evidence: detail.evidence.map(toCandidateEvidenceItem),
  }
}

function toCandidateSignalItem(signal: SignalResponse): CandidateDetailPresentation['signals'][number] {
  return {
    signalId: signal.signal_id,
    signalType: signal.signal_type,
    sourceSystem: signal.source_system,
    sourceRecordId: signal.source_record_id,
    affectedAssetKey: signal.affected_asset.asset_key,
    affectedAssetType: signal.affected_asset.asset_type,
    detectedAt: signal.detected_at,
    severity: signal.severity,
  }
}

function toCandidateEvidenceItem(
  evidence: EvidenceResponse,
): CandidateDetailPresentation['evidence'][number] {
  return {
    evidenceId: evidence.evidence_id,
    sourceSystem: evidence.source_system,
    sourceReference: evidence.source_reference,
    capturedAt: evidence.captured_at,
    referenceUri: evidence.reference_uri,
  }
}
