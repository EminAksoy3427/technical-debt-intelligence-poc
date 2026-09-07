import { describe, expect, it, vi } from 'vitest'
import { submitGovernedMutation } from '../../app/utils/submitGovernedAction'

function httpError(statusCode: number, detail: string) {
  return Object.assign(new Error(detail), { statusCode, data: { detail } })
}

describe('submitGovernedMutation', () => {
  it('does not retry a failed mutation', async () => {
    const mutate = vi.fn().mockRejectedValue(httpError(500, 'failed'))
    const refreshTechnicalDebt = vi.fn()

    const result = await submitGovernedMutation({ mutate, refreshTechnicalDebt })

    expect(result).toEqual({ status: 'error', resource: null })
    expect(mutate).toHaveBeenCalledTimes(1)
    expect(refreshTechnicalDebt).not.toHaveBeenCalled()
  })

  it('refreshes once after 409 without repeating the mutation', async () => {
    const mutate = vi.fn().mockRejectedValue(httpError(409, 'state changed'))
    const refreshTechnicalDebt = vi.fn().mockResolvedValue(undefined)

    const result = await submitGovernedMutation({ mutate, refreshTechnicalDebt })

    expect(result.status).toBe('conflict')
    expect(mutate).toHaveBeenCalledTimes(1)
    expect(refreshTechnicalDebt).toHaveBeenCalledTimes(1)
  })

  it('identifies unresolved reconciliation and still never retries', async () => {
    const mutate = vi
      .fn()
      .mockRejectedValue(httpError(409, 'External issue could not be reconciled'))
    const refreshTechnicalDebt = vi.fn().mockResolvedValue(undefined)

    const result = await submitGovernedMutation({
      mutate,
      refreshTechnicalDebt,
      recognizeReconciliationConflict: true,
    })

    expect(result.status).toBe('reconciliation-unresolved')
    expect(mutate).toHaveBeenCalledTimes(1)
  })

  it('preserves the persisted resource when refresh fails after success', async () => {
    const persisted = { id: 'persisted-resource' }
    const mutate = vi.fn().mockResolvedValue(persisted)
    const refreshTechnicalDebt = vi.fn().mockRejectedValue(new Error('network'))

    const result = await submitGovernedMutation({ mutate, refreshTechnicalDebt })

    expect(result).toEqual({ status: 'success-refresh-failed', resource: persisted })
    expect(mutate).toHaveBeenCalledTimes(1)
    expect(refreshTechnicalDebt).toHaveBeenCalledTimes(1)
  })
})
