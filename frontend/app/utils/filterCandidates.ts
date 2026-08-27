import type {
  CandidateAssetType,
  CandidateListItem,
  CandidateReviewStatus,
} from '../types/candidate'

export interface CandidateFilters {
  search?: string
  reviewStatus?: CandidateReviewStatus | ''
  assetType?: CandidateAssetType | ''
}

export function filterCandidates(
  candidates: CandidateListItem[],
  filters: CandidateFilters,
): CandidateListItem[] {
  const searchTerm = filters.search?.trim().toLowerCase() ?? ''

  return candidates.filter((candidate) => {
    const matchesSearch =
      !searchTerm ||
      candidate.title.toLowerCase().includes(searchTerm) ||
      candidate.assetName.toLowerCase().includes(searchTerm)
    const matchesReviewStatus =
      !filters.reviewStatus || candidate.reviewStatus === filters.reviewStatus
    const matchesAssetType = !filters.assetType || candidate.assetType === filters.assetType

    return matchesSearch && matchesReviewStatus && matchesAssetType
  })
}
