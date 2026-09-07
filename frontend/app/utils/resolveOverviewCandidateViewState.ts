export type OverviewCandidateViewState = 'loading' | 'error' | 'empty' | 'ready'

export function resolveOverviewCandidateViewState(input: {
  pending: boolean
  hasError: boolean
  hasListResponse: boolean
  candidateCount: number
}): OverviewCandidateViewState {
  if (input.hasError) {
    return 'error'
  }

  if (input.pending || !input.hasListResponse) {
    return 'loading'
  }

  if (input.candidateCount === 0) {
    return 'empty'
  }

  return 'ready'
}
