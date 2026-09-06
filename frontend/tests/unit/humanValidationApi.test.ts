import { describe, expect, it, vi } from 'vitest'
import {
  HumanValidationApiConfigurationError,
  createHumanValidationApi,
} from '../../app/composables/useHumanValidationApi'
import type { HumanValidationResponse } from '../../app/types/humanValidationApi'
import { buildHumanValidationRequest } from '../../app/utils/buildHumanValidationRequest'

const API_ORIGIN = 'https://human-validation-api.example.test'
const CANDIDATE_ID = '20000000-0000-0000-0000-000000000001'

const validateResponse: HumanValidationResponse = {
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
  governance: {
    state: 'VALIDATED',
    revision: 1,
  },
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

describe('createHumanValidationApi', () => {
  it('POSTs VALIDATE with rationale and expected revision only', async () => {
    const request = vi.fn().mockResolvedValue(validateResponse)
    const api = createHumanValidationApi({ apiBaseUrl: API_ORIGIN, request })
    const payload = buildHumanValidationRequest({
      decision: 'VALIDATE',
      expectedGovernanceRevision: 0,
      rationale: 'The Candidate is a validated structural issue.',
      requestedInformation: '',
    })

    const result = await api.createHumanDecision(CANDIDATE_ID, payload)

    expect(request).toHaveBeenCalledTimes(1)
    expect(request).toHaveBeenCalledWith(
      `${API_ORIGIN}/api/v1/candidates/${CANDIDATE_ID}/human-decisions`,
      { method: 'POST', body: payload },
    )
    expect(payload).toEqual({
      decision: 'VALIDATE',
      rationale: 'The Candidate is a validated structural issue.',
      expected_governance_revision: 0,
    })
    expect(result).toBe(validateResponse)
  })

  it('does not send actor, approval, role, or other authority fields', async () => {
    const request = vi.fn().mockResolvedValue(validateResponse)
    const api = createHumanValidationApi({ apiBaseUrl: API_ORIGIN, request })
    const payload = buildHumanValidationRequest({
      decision: 'VALIDATE',
      expectedGovernanceRevision: 2,
      rationale: '  Structural issue confirmed.  ',
      requestedInformation: 'should not be sent',
    })

    await api.createHumanDecision(CANDIDATE_ID, payload)

    const serializedCall = JSON.stringify(request.mock.calls[0])
    const [, options] = request.mock.calls[0] ?? []
    expect(options?.body).toEqual({
      decision: 'VALIDATE',
      rationale: 'Structural issue confirmed.',
      expected_governance_revision: 2,
    })
    expect(options?.body).not.toHaveProperty('actor_reference')
    expect(options?.body).not.toHaveProperty('role')
    expect(options?.body).not.toHaveProperty('approval')
    expect(options?.body).not.toHaveProperty('authorization')
    expect(options?.body).not.toHaveProperty('provider')
    expect(options?.body).not.toHaveProperty('model')
    expect(options?.body).not.toHaveProperty('tool')
    expect(options?.body).not.toHaveProperty('technical_debt_id')
    expect(options?.body).not.toHaveProperty('state')
    expect(serializedCall).not.toContain('actor_reference')
    expect(serializedCall).not.toContain('approval')
    expect(serializedCall).not.toContain('authorization')
    expect(serializedCall).not.toContain('provider')
    expect(serializedCall).not.toContain('"model"')
    expect(serializedCall).not.toContain('"tool"')
    expect(serializedCall).not.toContain('technical_debt_id')
  })

  it('POSTs REJECT with rationale and no TechnicalDebt fields', async () => {
    const request = vi.fn().mockResolvedValue({
      ...validateResponse,
      human_decision: {
        ...validateResponse.human_decision,
        decision: 'REJECT',
        rationale: 'The findings do not form a structural issue.',
      },
      governance: { state: 'REJECTED', revision: 1 },
      technical_debt: null,
    })
    const api = createHumanValidationApi({ apiBaseUrl: API_ORIGIN, request })
    const payload = buildHumanValidationRequest({
      decision: 'REJECT',
      expectedGovernanceRevision: 0,
      rationale: 'The findings do not form a structural issue.',
      requestedInformation: '',
    })

    await api.createHumanDecision(CANDIDATE_ID, payload)

    expect(payload).toEqual({
      decision: 'REJECT',
      rationale: 'The findings do not form a structural issue.',
      expected_governance_revision: 0,
    })
    expect(payload).not.toHaveProperty('requested_information')
  })

  it('POSTs REQUEST_INFO with requested information and the current revision', async () => {
    const request = vi.fn().mockResolvedValue({
      ...validateResponse,
      human_decision: {
        ...validateResponse.human_decision,
        decision: 'REQUEST_INFO',
        rationale: null,
        requested_information: 'Who owns the catalog service?',
      },
      governance: { state: 'INFORMATION_REQUESTED', revision: 1 },
      technical_debt: null,
    })
    const api = createHumanValidationApi({ apiBaseUrl: API_ORIGIN, request })
    const payload = buildHumanValidationRequest({
      decision: 'REQUEST_INFO',
      expectedGovernanceRevision: 1,
      rationale: '',
      requestedInformation: '  Who owns the catalog service?  ',
    })

    await api.createHumanDecision(CANDIDATE_ID, payload)

    expect(payload).toEqual({
      decision: 'REQUEST_INFO',
      requested_information: 'Who owns the catalog service?',
      expected_governance_revision: 1,
    })
    expect(payload).not.toHaveProperty('rationale')
  })

  it('fails before requesting when the public API base URL is missing', async () => {
    const request = vi.fn()
    const api = createHumanValidationApi({ apiBaseUrl: '', request })

    await expect(
      api.createHumanDecision(
        CANDIDATE_ID,
        buildHumanValidationRequest({
          decision: 'VALIDATE',
          expectedGovernanceRevision: 0,
          rationale: 'The Candidate is a validated structural issue.',
          requestedInformation: '',
        }),
      ),
    ).rejects.toBeInstanceOf(HumanValidationApiConfigurationError)
    expect(request).not.toHaveBeenCalled()
  })

  it('does not convert HTTP failures into a successful decision', async () => {
    const conflict = httpError(409, 'expected_governance_revision is stale')
    const unavailable = httpError(403, 'Human Validation is not available')

    await expect(
      createHumanValidationApi({
        apiBaseUrl: API_ORIGIN,
        request: vi.fn().mockRejectedValue(conflict),
      }).createHumanDecision(
        CANDIDATE_ID,
        buildHumanValidationRequest({
          decision: 'VALIDATE',
          expectedGovernanceRevision: 0,
          rationale: 'The Candidate is a validated structural issue.',
          requestedInformation: '',
        }),
      ),
    ).rejects.toBe(conflict)

    await expect(
      createHumanValidationApi({
        apiBaseUrl: API_ORIGIN,
        request: vi.fn().mockRejectedValue(unavailable),
      }).createHumanDecision(
        CANDIDATE_ID,
        buildHumanValidationRequest({
          decision: 'VALIDATE',
          expectedGovernanceRevision: 0,
          rationale: 'The Candidate is a validated structural issue.',
          requestedInformation: '',
        }),
      ),
    ).rejects.toMatchObject({
      statusCode: 403,
      data: { detail: 'Human Validation is not available' },
    })
  })
})
