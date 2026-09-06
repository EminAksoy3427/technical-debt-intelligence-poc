import { describe, expect, it } from 'vitest'
import { resolveTechnicalDebtPortfolioViewState } from '../../app/utils/resolveTechnicalDebtPortfolioViewState'

describe('resolveTechnicalDebtPortfolioViewState', () => {
  it('returns error when the list request failed', () => {
    expect(
      resolveTechnicalDebtPortfolioViewState({
        pending: false,
        hasError: true,
        hasListResponse: false,
        technicalDebtCount: 0,
      }),
    ).toBe('error')
  })

  it('returns loading while pending or before a list response arrives', () => {
    expect(
      resolveTechnicalDebtPortfolioViewState({
        pending: true,
        hasError: false,
        hasListResponse: false,
        technicalDebtCount: 0,
      }),
    ).toBe('loading')

    expect(
      resolveTechnicalDebtPortfolioViewState({
        pending: false,
        hasError: false,
        hasListResponse: false,
        technicalDebtCount: 0,
      }),
    ).toBe('loading')
  })

  it('returns empty when the API returned no TechnicalDebt records', () => {
    expect(
      resolveTechnicalDebtPortfolioViewState({
        pending: false,
        hasError: false,
        hasListResponse: true,
        technicalDebtCount: 0,
      }),
    ).toBe('empty')
  })

  it('returns ready when TechnicalDebt records exist', () => {
    expect(
      resolveTechnicalDebtPortfolioViewState({
        pending: false,
        hasError: false,
        hasListResponse: true,
        technicalDebtCount: 2,
      }),
    ).toBe('ready')
  })
})
