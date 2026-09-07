import { describe, expect, it, vi } from 'vitest'
import { buildHumanValidationRequest } from '../../app/utils/buildHumanValidationRequest'
import {
  classifyHumanValidationError,
  humanValidationSubmitMessage,
  submitHumanValidationDecision,
} from '../../app/utils/submitHumanValidationDecision'
import type { HumanValidationResponse } from '../../app/types/humanValidationApi'

const CANDIDATE_ID = '20000000-0000-0000-0000-000000000001'

const successResponse: HumanValidationResponse = {
  human_decision: {
    human_decision_id: '40000000-0000-0000-0000-000000000001',
    candidate_id: CANDIDATE_ID,
    sequence_number: 1,
    decision: 'VALIDATE',
    rationale: 'The Candidate is a validated structural issue.',
    requested_information: null,
    actor_reference: 'poc:local-reviewer',
    created_at: '2026-09-06T18:00:00+00:00',
  },
  governance: { state: 'VALIDATED', revision: 1 },
  technical_debt: {
    technical_debt_id: '50000000-0000-0000-0000-000000000001',
    lifecycle_status: 'REGISTERED',
    created_at: '2026-09-06T18:00:00+00:00',
    source_candidate_id: CANDIDATE_ID,
  },
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

describe('classifyHumanValidationError', () => {
  it('classifies 409 as conflict, 403 as unavailable, and other failures generically', () => {
    expect(classifyHumanValidationError({ statusCode: 409 })).toBe('conflict')
    expect(classifyHumanValidationError({ statusCode: 403 })).toBe('unavailable')
    expect(classifyHumanValidationError({ statusCode: 404 })).toBe('not-found')
    expect(classifyHumanValidationError({ statusCode: 422 })).toBe('invalid')
    expect(classifyHumanValidationError({ statusCode: 500 })).toBe('error')
    expect(classifyHumanValidationError(new Error('network'))).toBe('error')
  })
})

describe('humanValidationSubmitMessage', () => {
  it('uses a conflict message that requires refresh rather than retry', () => {
    expect(humanValidationSubmitMessage('conflict')).toBe(
      'This Candidate changed since you started reviewing. The latest state has been refreshed. Review it before recording a decision.',
    )
    expect(humanValidationSubmitMessage('conflict')).not.toContain('409')
    expect(humanValidationSubmitMessage('unavailable')).toBe('Human Validation is not available.')
  })

  it('says a saved decision persisted when only refresh failed', () => {
    expect(humanValidationSubmitMessage('success-refresh-failed')).toBe(
      'Human Validation was saved, but the latest governance state could not be refreshed.',
    )
    expect(humanValidationSubmitMessage('success-refresh-failed')).not.toContain('could not be submitted')
    expect(humanValidationSubmitMessage('conflict-refresh-failed')).toBe(
      'This Candidate changed since you started reviewing, but the latest state could not be refreshed.',
    )
    expect(humanValidationSubmitMessage('conflict-refresh-failed')).not.toContain('was saved')
  })
})

describe('submitHumanValidationDecision', () => {
  const payload = buildHumanValidationRequest({
    decision: 'VALIDATE',
    expectedGovernanceRevision: 0,
    rationale: 'The Candidate is a validated structural issue.',
    requestedInformation: '',
  })

  it('refreshes Candidate Detail after a successful mutation', async () => {
    const createHumanDecision = vi.fn().mockResolvedValue(successResponse)
    const refreshCandidate = vi.fn().mockResolvedValue(undefined)

    const result = await submitHumanValidationDecision({
      candidateId: CANDIDATE_ID,
      payload,
      createHumanDecision,
      refreshCandidate,
    })

    expect(result).toBe('success')
    expect(createHumanDecision).toHaveBeenCalledTimes(1)
    expect(createHumanDecision).toHaveBeenCalledWith(CANDIDATE_ID, payload)
    expect(refreshCandidate).toHaveBeenCalledTimes(1)
  })

  it('returns success-refresh-failed when POST persists and refresh fails', async () => {
    const createHumanDecision = vi.fn().mockResolvedValue(successResponse)
    const refreshCandidate = vi.fn().mockRejectedValue(httpError(500, 'Candidate refresh failed'))

    const result = await submitHumanValidationDecision({
      candidateId: CANDIDATE_ID,
      payload,
      createHumanDecision,
      refreshCandidate,
    })

    expect(result).toBe('success-refresh-failed')
    expect(createHumanDecision).toHaveBeenCalledTimes(1)
    expect(refreshCandidate).toHaveBeenCalledTimes(1)
    expect(humanValidationSubmitMessage(result)).toContain('was saved')
    expect(humanValidationSubmitMessage(result)).toContain('could not be refreshed')
    expect(humanValidationSubmitMessage(result)).not.toContain('could not be submitted')
  })

  it('shows conflict, refreshes Candidate, and does not retry the mutation', async () => {
    const createHumanDecision = vi
      .fn()
      .mockRejectedValue(httpError(409, 'expected_governance_revision is stale'))
    const refreshCandidate = vi.fn().mockResolvedValue(undefined)

    const result = await submitHumanValidationDecision({
      candidateId: CANDIDATE_ID,
      payload,
      createHumanDecision,
      refreshCandidate,
    })

    expect(result).toBe('conflict')
    expect(createHumanDecision).toHaveBeenCalledTimes(1)
    expect(refreshCandidate).toHaveBeenCalledTimes(1)
  })

  it('returns conflict-refresh-failed without retrying mutation when 409 refresh fails', async () => {
    const createHumanDecision = vi
      .fn()
      .mockRejectedValue(httpError(409, 'expected_governance_revision is stale'))
    const refreshCandidate = vi.fn().mockRejectedValue(httpError(500, 'Candidate refresh failed'))

    const result = await submitHumanValidationDecision({
      candidateId: CANDIDATE_ID,
      payload,
      createHumanDecision,
      refreshCandidate,
    })

    expect(result).toBe('conflict-refresh-failed')
    expect(createHumanDecision).toHaveBeenCalledTimes(1)
    expect(refreshCandidate).toHaveBeenCalledTimes(1)
    expect(humanValidationSubmitMessage(result)).not.toContain('was saved')
    expect(humanValidationSubmitMessage(result)).toContain('could not be refreshed')
  })

  it('returns unavailable for 403 without treating it as success', async () => {
    const createHumanDecision = vi
      .fn()
      .mockRejectedValue(httpError(403, 'Human Validation is not available'))
    const refreshCandidate = vi.fn().mockResolvedValue(undefined)

    const result = await submitHumanValidationDecision({
      candidateId: CANDIDATE_ID,
      payload,
      createHumanDecision,
      refreshCandidate,
    })

    expect(result).toBe('unavailable')
    expect(createHumanDecision).toHaveBeenCalledTimes(1)
    expect(refreshCandidate).not.toHaveBeenCalled()
  })

  it('preserves a failed mutation without a second create call', async () => {
    const createHumanDecision = vi.fn().mockRejectedValue(httpError(500, 'persist failed'))
    const refreshCandidate = vi.fn().mockResolvedValue(undefined)

    const result = await submitHumanValidationDecision({
      candidateId: CANDIDATE_ID,
      payload,
      createHumanDecision,
      refreshCandidate,
    })

    expect(result).toBe('error')
    expect(createHumanDecision).toHaveBeenCalledTimes(1)
    expect(refreshCandidate).not.toHaveBeenCalled()
  })
})
