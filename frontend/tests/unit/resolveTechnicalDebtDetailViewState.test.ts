import { describe, expect, it } from 'vitest'
import type { TechnicalDebtDetail } from '../../app/types/technicalDebtApi'
import {
  resolveTechnicalDebtDetailErrorState,
  resolveTechnicalDebtDetailViewState,
} from '../../app/utils/resolveTechnicalDebtDetailViewState'

const TECHNICAL_DEBT_ID = '50000000-0000-0000-0000-000000000001'
const OTHER_TECHNICAL_DEBT_ID = '50000000-0000-0000-0000-000000000002'

const detail = {
  technical_debt_id: TECHNICAL_DEBT_ID,
} as TechnicalDebtDetail

describe('resolveTechnicalDebtDetailErrorState', () => {
  it('resolves HTTP 404 to not-found and 422 to invalid-identifier', () => {
    expect(resolveTechnicalDebtDetailErrorState({ statusCode: 404 })).toBe('not-found')
    expect(resolveTechnicalDebtDetailErrorState({ statusCode: 422 })).toBe('invalid-identifier')
    expect(resolveTechnicalDebtDetailErrorState({ statusCode: 500 })).toBe('error')
  })
})

describe('resolveTechnicalDebtDetailViewState', () => {
  it('returns loading while the Detail request is in progress', () => {
    expect(
      resolveTechnicalDebtDetailViewState({
        pending: true,
        error: null,
        detail: undefined,
        requestedTechnicalDebtId: TECHNICAL_DEBT_ID,
      }),
    ).toBe('loading')
  })

  it('does not present stale TechnicalDebt data for a different route ID', () => {
    expect(
      resolveTechnicalDebtDetailViewState({
        pending: false,
        error: null,
        detail,
        requestedTechnicalDebtId: OTHER_TECHNICAL_DEBT_ID,
      }),
    ).toBe('loading')
  })

  it('returns success only when the response TechnicalDebt ID matches the route', () => {
    expect(
      resolveTechnicalDebtDetailViewState({
        pending: false,
        error: null,
        detail,
        requestedTechnicalDebtId: TECHNICAL_DEBT_ID,
      }),
    ).toBe('success')
  })

  it('does not convert API failure into a successful Detail', () => {
    expect(
      resolveTechnicalDebtDetailViewState({
        pending: false,
        error: { statusCode: 404 },
        detail,
        requestedTechnicalDebtId: TECHNICAL_DEBT_ID,
      }),
    ).toBe('not-found')
  })
})
