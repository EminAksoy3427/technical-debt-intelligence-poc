import { describe, expect, it, vi } from 'vitest'
import {
  AgentRunApiConfigurationError,
  createAgentRunApi,
} from '../../app/composables/useAgentRunApi'
import type { AgentRunResponse } from '../../app/types/agentRunApi'

const API_ORIGIN = 'https://agent-run-api.example.test'
const CANDIDATE_ID = '20000000-0000-0000-0000-000000000001'
const AGENT_RUN_ID = '30000000-0000-0000-0000-000000000001'

const completedPayload: AgentRunResponse = {
  agent_run_id: AGENT_RUN_ID,
  candidate_id: CANDIDATE_ID,
  status: 'COMPLETED',
  created_at: '2026-09-05T10:00:00+00:00',
  started_at: '2026-09-05T10:00:00+00:00',
  completed_at: '2026-09-05T10:00:01+00:00',
  stop_reason: null,
  structured_assessment: {
    outcome: 'SUPPORTED',
    conclusion: {
      statement: 'Persisted Evidence is available for human review.',
      references: [
        {
          reference_type: 'EVIDENCE',
          evidence_id: '10000000-0000-0000-0000-000000000011',
        },
      ],
    },
    supporting_claims: [],
    missing_evidence: [],
    uncertainties: [],
    recommendation: 'An authorized human must decide any Candidate lifecycle action.',
    stop_reason: null,
  },
  tool_executions: [],
  policy_decisions: [],
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

describe('createAgentRunApi', () => {
  it('POSTs to the Candidate AgentRun collection with no request body', async () => {
    const request = vi.fn().mockResolvedValue(completedPayload)
    const api = createAgentRunApi({ apiBaseUrl: API_ORIGIN, request })

    const result = await api.startCandidateInvestigation(CANDIDATE_ID)

    expect(request).toHaveBeenCalledTimes(1)
    expect(request).toHaveBeenCalledWith(
      `${API_ORIGIN}/api/v1/candidates/${CANDIDATE_ID}/agent-runs`,
      { method: 'POST' },
    )
    const [, options] = request.mock.calls[0] ?? []
    expect(options).toEqual({ method: 'POST' })
    expect(options).not.toHaveProperty('body')
    expect(JSON.stringify(options)).not.toContain('prompt')
    expect(JSON.stringify(options)).not.toContain('tools')
    expect(JSON.stringify(options)).not.toContain('provider')
    expect(JSON.stringify(options)).not.toContain('model')
    expect(JSON.stringify(options)).not.toContain('approval')
    expect(JSON.stringify(options)).not.toContain('effect')
    expect(JSON.stringify(options)).not.toContain('risk')
    expect(JSON.stringify(options)).not.toContain('scope')
    expect(result).toBe(completedPayload)
  })

  it('does not send prompt, tool, authorization, or provider controls', async () => {
    const request = vi.fn().mockResolvedValue(completedPayload)
    const api = createAgentRunApi({ apiBaseUrl: API_ORIGIN, request })

    await api.startCandidateInvestigation(CANDIDATE_ID)

    const serializedCall = JSON.stringify(request.mock.calls[0])
    expect(serializedCall).not.toMatch(/system instructions/i)
    expect(serializedCall).not.toContain('write_candidate')
    expect(serializedCall).not.toContain('OPENAI')
    expect(serializedCall).not.toContain('GPT')
  })

  it('GETs a Candidate-scoped AgentRun by both identifiers', async () => {
    const request = vi.fn().mockResolvedValue(completedPayload)
    const api = createAgentRunApi({ apiBaseUrl: API_ORIGIN, request })

    const result = await api.getCandidateInvestigation(CANDIDATE_ID, AGENT_RUN_ID)

    expect(request).toHaveBeenCalledTimes(1)
    expect(request).toHaveBeenCalledWith(
      `${API_ORIGIN}/api/v1/candidates/${CANDIDATE_ID}/agent-runs/${AGENT_RUN_ID}`,
    )
    const [, options] = request.mock.calls[0] ?? []
    expect(options).toBeUndefined()
    expect(result).toBe(completedPayload)
  })

  it('does not introduce a duplicate slash when the API base URL has a trailing slash', async () => {
    const request = vi.fn().mockResolvedValue(completedPayload)
    const api = createAgentRunApi({ apiBaseUrl: `${API_ORIGIN}/`, request })

    await api.startCandidateInvestigation(CANDIDATE_ID)
    await api.getCandidateInvestigation(CANDIDATE_ID, AGENT_RUN_ID)

    expect(request).toHaveBeenNthCalledWith(
      1,
      `${API_ORIGIN}/api/v1/candidates/${CANDIDATE_ID}/agent-runs`,
      { method: 'POST' },
    )
    expect(request).toHaveBeenNthCalledWith(
      2,
      `${API_ORIGIN}/api/v1/candidates/${CANDIDATE_ID}/agent-runs/${AGENT_RUN_ID}`,
    )
  })

  it('returns the wire JSON without presentation or governance mapping', async () => {
    const request = vi.fn().mockResolvedValue(completedPayload)
    const api = createAgentRunApi({ apiBaseUrl: API_ORIGIN, request })

    const result = await api.startCandidateInvestigation(CANDIDATE_ID)

    expect(result).toEqual(completedPayload)
    expect(result).toHaveProperty('agent_run_id', AGENT_RUN_ID)
    expect(result).toHaveProperty('structured_assessment')
    expect(result).not.toHaveProperty('agentRunId')
    expect(result).not.toHaveProperty('validated')
    expect(result).not.toHaveProperty('rejected')
    expect(result).not.toHaveProperty('confidence')
    expect(result).not.toHaveProperty('riskScore')
  })

  it('fails before requesting when the public API base URL is missing', async () => {
    const request = vi.fn()
    const api = createAgentRunApi({ apiBaseUrl: '', request })

    await expect(api.startCandidateInvestigation(CANDIDATE_ID)).rejects.toBeInstanceOf(
      AgentRunApiConfigurationError,
    )
    await expect(api.getCandidateInvestigation(CANDIDATE_ID, AGENT_RUN_ID)).rejects.toThrow(
      'Public API base URL is not configured',
    )
    expect(request).not.toHaveBeenCalled()
  })

  it('fails before requesting when the public API base URL is blank', async () => {
    const request = vi.fn()
    const api = createAgentRunApi({ apiBaseUrl: '   ', request })

    await expect(api.startCandidateInvestigation(CANDIDATE_ID)).rejects.toThrow(
      'Public API base URL is not configured',
    )
    expect(request).not.toHaveBeenCalled()
  })

  it('does not convert HTTP failures into a successful investigation', async () => {
    const notFoundCandidate = httpError(404, 'Candidate not found')
    const notFoundRun = httpError(404, 'AgentRun not found')
    const unexpected = httpError(500, 'Agent investigation could not be started')

    await expect(
      createAgentRunApi({
        apiBaseUrl: API_ORIGIN,
        request: vi.fn().mockRejectedValue(notFoundCandidate),
      }).startCandidateInvestigation(CANDIDATE_ID),
    ).rejects.toBe(notFoundCandidate)

    await expect(
      createAgentRunApi({
        apiBaseUrl: API_ORIGIN,
        request: vi.fn().mockRejectedValue(notFoundRun),
      }).getCandidateInvestigation(CANDIDATE_ID, AGENT_RUN_ID),
    ).rejects.toMatchObject({ statusCode: 404, data: { detail: 'AgentRun not found' } })

    await expect(
      createAgentRunApi({
        apiBaseUrl: API_ORIGIN,
        request: vi.fn().mockRejectedValue(unexpected),
      }).startCandidateInvestigation(CANDIDATE_ID),
    ).rejects.toMatchObject({ statusCode: 500 })
  })
})
