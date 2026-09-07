export const OVERVIEW_CANDIDATES_FOR_REVIEW_LIMIT = 5

/**
 * Preserves list-API order. The Candidate list is a stable factual order,
 * not recency or priority.
 */
export function selectCandidatesForReview<T>(
  candidates: readonly T[],
  limit = OVERVIEW_CANDIDATES_FOR_REVIEW_LIMIT,
): T[] {
  return candidates.slice(0, limit)
}
