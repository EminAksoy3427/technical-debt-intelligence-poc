import { describe, expect, it, vi } from 'vitest'
import type { ActionProposal } from '../../app/types/technicalDebtApi'
import {
  actionPreparationSubmitMessage,
  classifyActionPreparationError,
  submitActionPreparation,
} from '../../app/utils/submitActionPreparation'

const TECHNICAL_DEBT_ID = '50000000-0000-0000-0000-000000000001'

const proposal: ActionProposal = {
  action_proposal_id: '60000000-0000-0000-0000-000000000001',
  technical_debt_id: TECHNICAL_DEBT_ID,
  action_type: 'CREATE_GITHUB_ISSUE',
  target_repository_owner: 'tdi-demo-target',
  target_repository_name: 'tdi-action-preview',
  title: 'Technical debt: svc-orbit-catalog',
  body: 'Exact backend body',
  payload_fingerprint: 'abc123fingerprint',
  reconciliation_marker: 'tdiq-action-proposal:60000000-0000-0000-0000-000000000001',
  prepared_by: 'poc:local-reviewer',
  created_at: '2026-09-07T16:00:00+00:00',
}

function httpError(statusCode: number, detail: string) {
  const error = new Error(detail) as Error & {
    statusCode: number
    data: { detail: string }
  }
  error.statusCode = statusCode
  error.data = { detail }
  return error
}

describe('classifyActionPreparationError', () => {
  it('classifies 503 as unavailable and does not retry semantics', () => {
    expect(classifyActionPreparationError({ statusCode: 503 })).toBe('unavailable')
    expect(classifyActionPreparationError({ statusCode: 404 })).toBe('not-found')
    expect(classifyActionPreparationError({ statusCode: 409 })).toBe('conflict')
    expect(classifyActionPreparationError({ statusCode: 422 })).toBe('invalid')
    expect(classifyActionPreparationError({ statusCode: 500 })).toBe('error')
    expect(classifyActionPreparationError(new Error('network'))).toBe('error')
  })
})

describe('actionPreparationSubmitMessage', () => {
  it('says the preview was prepared when only refresh failed', () => {
    expect(actionPreparationSubmitMessage('success-refresh-failed')).toBe(
      'The GitHub issue preview was prepared, but TechnicalDebt details could not be refreshed.',
    )
    expect(actionPreparationSubmitMessage('success-refresh-failed')).not.toContain(
      'could not be prepared',
    )
    expect(actionPreparationSubmitMessage('error')).toBe(
      'The GitHub issue preview could not be prepared.',
    )
  })
})

describe('submitActionPreparation', () => {
  it('refreshes TechnicalDebt detail after a successful prepare', async () => {
    const prepareActionProposal = vi.fn().mockResolvedValue(proposal)
    const refreshTechnicalDebt = vi.fn().mockResolvedValue(undefined)

    const result = await submitActionPreparation({
      technicalDebtId: TECHNICAL_DEBT_ID,
      prepareActionProposal,
      refreshTechnicalDebt,
    })

    expect(result).toEqual({ status: 'success', proposal })
    expect(prepareActionProposal).toHaveBeenCalledTimes(1)
    expect(prepareActionProposal).toHaveBeenCalledWith(TECHNICAL_DEBT_ID)
    expect(refreshTechnicalDebt).toHaveBeenCalledTimes(1)
  })

  it('returns the persisted proposal when POST succeeds and refresh fails', async () => {
    const prepareActionProposal = vi.fn().mockResolvedValue(proposal)
    const refreshTechnicalDebt = vi.fn().mockRejectedValue(httpError(500, 'refresh failed'))

    const result = await submitActionPreparation({
      technicalDebtId: TECHNICAL_DEBT_ID,
      prepareActionProposal,
      refreshTechnicalDebt,
    })

    expect(result.status).toBe('success-refresh-failed')
    expect(result.proposal).toBe(proposal)
    expect(prepareActionProposal).toHaveBeenCalledTimes(1)
    expect(refreshTechnicalDebt).toHaveBeenCalledTimes(1)
    expect(actionPreparationSubmitMessage(result.status)).toContain('was prepared')
    expect(actionPreparationSubmitMessage(result.status)).not.toContain('could not be prepared')
  })

  it('does not retry POST after a network or 5xx failure', async () => {
    const prepareActionProposal = vi.fn().mockRejectedValue(httpError(500, 'persist failed'))
    const refreshTechnicalDebt = vi.fn().mockResolvedValue(undefined)

    const result = await submitActionPreparation({
      technicalDebtId: TECHNICAL_DEBT_ID,
      prepareActionProposal,
      refreshTechnicalDebt,
    })

    expect(result).toEqual({ status: 'error', proposal: null })
    expect(prepareActionProposal).toHaveBeenCalledTimes(1)
    expect(refreshTechnicalDebt).not.toHaveBeenCalled()
  })

  it('does not retry POST after 409 or 503', async () => {
    const conflictPrepare = vi.fn().mockRejectedValue(httpError(409, 'conflict'))
    const unavailablePrepare = vi.fn().mockRejectedValue(httpError(503, 'unavailable'))
    const refreshTechnicalDebt = vi.fn().mockResolvedValue(undefined)

    const conflict = await submitActionPreparation({
      technicalDebtId: TECHNICAL_DEBT_ID,
      prepareActionProposal: conflictPrepare,
      refreshTechnicalDebt,
    })
    const unavailable = await submitActionPreparation({
      technicalDebtId: TECHNICAL_DEBT_ID,
      prepareActionProposal: unavailablePrepare,
      refreshTechnicalDebt,
    })

    expect(conflict.status).toBe('conflict')
    expect(unavailable.status).toBe('unavailable')
    expect(conflictPrepare).toHaveBeenCalledTimes(1)
    expect(unavailablePrepare).toHaveBeenCalledTimes(1)
    expect(refreshTechnicalDebt).not.toHaveBeenCalled()
  })
})
