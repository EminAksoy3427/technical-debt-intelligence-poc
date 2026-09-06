import type { TechnicalDebtDetail } from '../types/technicalDebtApi'
import { httpStatusFromUnknownError } from './resolveCandidateDetailViewState'

export type TechnicalDebtDetailViewState =
  | 'loading'
  | 'success'
  | 'not-found'
  | 'invalid-identifier'
  | 'error'

export function resolveTechnicalDebtDetailErrorState(
  error: unknown,
): Exclude<TechnicalDebtDetailViewState, 'loading' | 'success'> {
  const status = httpStatusFromUnknownError(error)
  if (status === 404) {
    return 'not-found'
  }
  if (status === 422) {
    return 'invalid-identifier'
  }
  return 'error'
}

export function resolveTechnicalDebtDetailViewState(input: {
  pending: boolean
  error: unknown
  detail: TechnicalDebtDetail | null | undefined
  requestedTechnicalDebtId: string
}): TechnicalDebtDetailViewState {
  if (input.pending) {
    return 'loading'
  }

  if (input.error) {
    return resolveTechnicalDebtDetailErrorState(input.error)
  }

  if (
    input.detail == null ||
    input.detail.technical_debt_id !== input.requestedTechnicalDebtId
  ) {
    return 'loading'
  }

  return 'success'
}
