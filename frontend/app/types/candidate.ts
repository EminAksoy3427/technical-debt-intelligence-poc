/**
 * Frontend presentation model for the Candidate Pool.
 * This is not the canonical backend Candidate contract.
 */
export type CandidateReviewStatus = 'awaiting_review' | 'needs_information'

export type CandidateAssetType = 'application' | 'service' | 'data_store'

export interface CandidateListItem {
  id: string
  title: string
  assetName: string
  assetType: CandidateAssetType
  reviewStatus: CandidateReviewStatus
  suggestedTeam: string
  contributingSignalCount: number
  evidenceItemCount: number
}

/**
 * Presentation-only enterprise context for a Candidate under review.
 * Asset criticality provides asset context; it is not a technical-debt risk score.
 */
export interface CandidateContextSummary {
  assetCriticality: 'low' | 'medium' | 'high'
  dependencySummary: string
}

/**
 * Presentation-only evidence summary supporting Candidate review.
 * This is not a canonical backend evidence contract.
 */
export interface CandidateEvidenceItem {
  id: string
  sourceLabel: string
  summary: string
}

/**
 * Presentation model for the Candidate Detail view.
 * It remains distinct from the canonical backend Candidate contract and TechnicalDebt.
 */
export interface CandidateDetailView {
  id: string
  title: string
  reviewStatus: CandidateReviewStatus
  assetName: string
  assetType: CandidateAssetType
  suggestedTeam: string
  context: CandidateContextSummary
  evidence: CandidateEvidenceItem[]
}
