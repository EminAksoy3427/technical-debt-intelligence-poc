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
