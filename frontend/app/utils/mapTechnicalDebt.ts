import type {
  TechnicalDebtCreationDecisionPresentation,
  TechnicalDebtDetailPresentation,
  TechnicalDebtListItem,
  TechnicalDebtSourceCandidatePresentation,
} from '../types/technicalDebt'
import type {
  TechnicalDebtCreationDecision,
  TechnicalDebtDetail,
  TechnicalDebtSourceCandidate,
  TechnicalDebtSummary,
} from '../types/technicalDebtApi'

export function toTechnicalDebtListItem(summary: TechnicalDebtSummary): TechnicalDebtListItem {
  return {
    technicalDebtId: summary.technical_debt_id,
    lifecycleStatus: summary.lifecycle_status,
    createdAt: summary.created_at,
    sourceCandidateId: summary.source_candidate_id,
    hypothesis: summary.hypothesis,
    canonicalAssetKey: summary.canonical_asset.asset_key,
    canonicalAssetType: summary.canonical_asset.asset_type,
  }
}

export function toTechnicalDebtDetailPresentation(
  detail: TechnicalDebtDetail,
): TechnicalDebtDetailPresentation {
  return {
    technicalDebtId: detail.technical_debt_id,
    lifecycleStatus: detail.lifecycle_status,
    createdAt: detail.created_at,
    sourceCandidate: toSourceCandidatePresentation(detail.source_candidate),
    creationHumanDecision: toCreationDecisionPresentation(detail.creation_human_decision),
  }
}

function toSourceCandidatePresentation(
  candidate: TechnicalDebtSourceCandidate,
): TechnicalDebtSourceCandidatePresentation {
  return {
    candidateId: candidate.candidate_id,
    hypothesis: candidate.hypothesis,
    correlationRationale: candidate.correlation_rationale,
    canonicalAssetKey: candidate.canonical_asset.asset_key,
    canonicalAssetType: candidate.canonical_asset.asset_type,
  }
}

function toCreationDecisionPresentation(
  decision: TechnicalDebtCreationDecision,
): TechnicalDebtCreationDecisionPresentation {
  return {
    humanDecisionId: decision.human_decision_id,
    decision: decision.decision,
    sequenceNumber: decision.sequence_number,
    rationale: decision.rationale,
    actorReference: decision.actor_reference,
    createdAt: decision.created_at,
  }
}
