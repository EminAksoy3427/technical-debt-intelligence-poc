import type { CandidateListItem } from '../types/candidate'

export interface CandidateFilters {
  search?: string
  assetType?: CandidateListItem['assetType'] | ''
}

export function areCandidateFiltersActive(filters: CandidateFilters): boolean {
  return Boolean(filters.search?.trim()) || Boolean(filters.assetType)
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
      candidate.presentationTitle.toLowerCase().includes(searchTerm) ||
      candidate.assetName.toLowerCase().includes(searchTerm)
    const matchesAssetType = !filters.assetType || candidate.assetType === filters.assetType

    return matchesSearch && matchesAssetType
  })
}
