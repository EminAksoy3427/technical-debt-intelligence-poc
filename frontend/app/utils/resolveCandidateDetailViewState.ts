import type { CandidateDetailResponse } from '../types/candidateApi'

export type CandidateDetailViewState =
  | 'loading'
  | 'success'
  | 'not-found'
  | 'invalid-identifier'
  | 'error'

export function httpStatusFromUnknownError(error: unknown): number | undefined {
  if (error == null || typeof error !== 'object') {
    return undefined
  }

  const record = error as { statusCode?: unknown; status?: unknown }
  if (typeof record.statusCode === 'number') {
    return record.statusCode
  }
  if (typeof record.status === 'number') {
    return record.status
  }

  return undefined
}

export function resolveCandidateDetailErrorState(
  error: unknown,
): Exclude<CandidateDetailViewState, 'loading' | 'success'> {
  const status = httpStatusFromUnknownError(error)
  if (status === 404) {
    return 'not-found'
  }
  if (status === 422) {
    return 'invalid-identifier'
  }
  return 'error'
}

export function resolveCandidateDetailViewState(input: {
  pending: boolean
  error: unknown
  detail: CandidateDetailResponse | null | undefined
  requestedCandidateId: string
}): CandidateDetailViewState {
  if (input.pending) {
    return 'loading'
  }

  if (input.error) {
    return resolveCandidateDetailErrorState(input.error)
  }

  if (
    input.detail == null ||
    input.detail.candidate.candidate_id !== input.requestedCandidateId
  ) {
    return 'loading'
  }

  return 'success'
}
