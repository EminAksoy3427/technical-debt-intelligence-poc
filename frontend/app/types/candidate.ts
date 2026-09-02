import type { AssetType } from './candidateApi'

/**
 * Frontend presentation model for the Candidate Pool.
 * Mapped from CandidateSummaryResponse for pool display and client-side filtering.
 * This is not the canonical backend Candidate contract and is not TechnicalDebt.
 */
export interface CandidateListItem {
  id: string
  title: string
  assetName: string
  assetType: AssetType
  signalCount: number
  evidenceCount: number
}

export const candidatePoolAssetTypeLabels: Record<AssetType, string> = {
  APPLICATION: 'Application',
  SERVICE: 'Service',
  REPOSITORY: 'Repository',
}

/**
 * Presentation-only review status for the mock Candidate Detail view.
 * The Candidate Pool does not use this field.
 */
export type CandidateReviewStatus = 'awaiting_review' | 'needs_information'

/**
 * Presentation-only asset vocabulary for the mock Candidate Detail view.
 * The Candidate Pool uses AssetType from the Candidate list API instead.
 */
export type CandidateAssetType = 'application' | 'service' | 'data_store'

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
