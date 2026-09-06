export type TechnicalDebtPortfolioViewState = 'loading' | 'error' | 'empty' | 'ready'

export function resolveTechnicalDebtPortfolioViewState(input: {
  pending: boolean
  hasError: boolean
  hasListResponse: boolean
  technicalDebtCount: number
}): TechnicalDebtPortfolioViewState {
  if (input.hasError) {
    return 'error'
  }

  if (input.pending || !input.hasListResponse) {
    return 'loading'
  }

  if (input.technicalDebtCount === 0) {
    return 'empty'
  }

  return 'ready'
}
