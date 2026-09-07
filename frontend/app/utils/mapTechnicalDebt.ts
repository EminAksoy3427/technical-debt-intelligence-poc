import type {
  ActionProposalPresentation,
  TechnicalDebtCreationDecisionPresentation,
  TechnicalDebtDetailPresentation,
  TechnicalDebtListItem,
  TechnicalDebtSourceCandidatePresentation,
} from '../types/technicalDebt'
import type {
  ActionProposal,
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
    actionProposals: detail.action_proposals.map(toActionProposalPresentation),
  }
}

export function toActionProposalPresentation(proposal: ActionProposal): ActionProposalPresentation {
  return {
    actionProposalId: proposal.action_proposal_id,
    technicalDebtId: proposal.technical_debt_id,
    actionType: proposal.action_type,
    targetRepositoryOwner: proposal.target_repository_owner,
    targetRepositoryName: proposal.target_repository_name,
    title: proposal.title,
    body: proposal.body,
    payloadFingerprint: proposal.payload_fingerprint,
    reconciliationMarker: proposal.reconciliation_marker,
    preparedBy: proposal.prepared_by,
    createdAt: proposal.created_at,
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
