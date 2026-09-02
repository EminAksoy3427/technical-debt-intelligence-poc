export type CandidatePoolViewState =
  | 'loading'
  | 'error'
  | 'empty'
  | 'filtered-empty'
  | 'ready'

export function resolveCandidatePoolViewState(input: {
  pending: boolean
  hasError: boolean
  hasListResponse: boolean
  candidateCount: number
  filteredCount: number
}): CandidatePoolViewState {
  if (input.hasError) {
    return 'error'
  }

  if (input.pending || !input.hasListResponse) {
    return 'loading'
  }

  if (input.candidateCount === 0) {
    return 'empty'
  }

  if (input.filteredCount === 0) {
    return 'filtered-empty'
  }

  return 'ready'
}
