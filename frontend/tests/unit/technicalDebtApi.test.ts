import { describe, expect, it, vi } from 'vitest'
import {
  TechnicalDebtApiConfigurationError,
  createTechnicalDebtApi,
} from '../../app/composables/useTechnicalDebtApi'
import type {
  ActionApproval,
  ActionExecution,
  ActionProposal,
  ActionVerification,
  TechnicalDebtDetail,
  TechnicalDebtListResponse,
} from '../../app/types/technicalDebtApi'

const API_ORIGIN = 'https://technical-debt-api.example.test'
const TECHNICAL_DEBT_ID = '50000000-0000-0000-0000-000000000001'
const CANDIDATE_ID = '20000000-0000-0000-0000-000000000001'

const listPayload: TechnicalDebtListResponse = {
  items: [
    {
      technical_debt_id: TECHNICAL_DEBT_ID,
      lifecycle_status: 'REGISTERED',
      created_at: '2026-09-06T19:01:00+00:00',
      source_candidate_id: CANDIDATE_ID,
      hypothesis: 'Potential missing request timeout',
      canonical_asset: {
        asset_key: 'svc-orbit-catalog',
        asset_type: 'SERVICE',
      },
    },
  ],
  count: 1,
}

const detailPayload: TechnicalDebtDetail = {
  technical_debt_id: TECHNICAL_DEBT_ID,
  lifecycle_status: 'REGISTERED',
  created_at: '2026-09-06T19:01:00+00:00',
  source_candidate: {
    candidate_id: CANDIDATE_ID,
    hypothesis: 'Potential missing request timeout',
    correlation_rationale: 'Exact canonical asset and deterministic problem family.',
    canonical_asset: {
      asset_key: 'svc-orbit-catalog',
      asset_type: 'SERVICE',
    },
  },
  creation_human_decision: {
    human_decision_id: '40000000-0000-0000-0000-000000000001',
    decision: 'VALIDATE',
    sequence_number: 1,
    rationale: 'The Candidate is a validated structural issue.',
    actor_reference: 'poc:local-reviewer',
    created_at: '2026-09-06T19:01:00+00:00',
  },
  action_proposals: [],
  action_approvals: [],
  action_policy_decisions: [],
  action_executions: [],
  action_verifications: [],
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

describe('createTechnicalDebtApi', () => {
  it('calls the TechnicalDebt list endpoint with the configured API base URL', async () => {
    const request = vi.fn().mockResolvedValue(listPayload)
    const api = createTechnicalDebtApi({ apiBaseUrl: API_ORIGIN, request })

    const result = await api.listTechnicalDebts()

    expect(request).toHaveBeenCalledWith(`${API_ORIGIN}/api/v1/technical-debts`)
    expect(result).toBe(listPayload)
  })

  it('calls the TechnicalDebt detail endpoint with the TechnicalDebt UUID', async () => {
    const request = vi.fn().mockResolvedValue(detailPayload)
    const api = createTechnicalDebtApi({ apiBaseUrl: API_ORIGIN, request })

    const result = await api.getTechnicalDebt(TECHNICAL_DEBT_ID)

    expect(request).toHaveBeenCalledWith(
      `${API_ORIGIN}/api/v1/technical-debts/${TECHNICAL_DEBT_ID}`,
    )
    expect(result).toBe(detailPayload)
  })

  it('does not introduce a duplicate slash when the API base URL has a trailing slash', async () => {
    const request = vi.fn().mockResolvedValue(listPayload)
    const api = createTechnicalDebtApi({ apiBaseUrl: `${API_ORIGIN}/`, request })

    await api.listTechnicalDebts()

    expect(request).toHaveBeenCalledWith(`${API_ORIGIN}/api/v1/technical-debts`)
  })

  it('returns the wire JSON without inventing risk, effort, or owner fields', async () => {
    const request = vi.fn().mockResolvedValue(listPayload)
    const api = createTechnicalDebtApi({ apiBaseUrl: API_ORIGIN, request })

    const result = await api.listTechnicalDebts()
    const item = result.items[0]
    const serialized = JSON.stringify(result)

    expect(item).toEqual(listPayload.items[0])
    expect(item).not.toHaveProperty('risk')
    expect(item).not.toHaveProperty('effort')
    expect(item).not.toHaveProperty('owner')
    expect(item).not.toHaveProperty('priority')
    expect(serialized).not.toContain('validated_owner')
    expect(serialized).not.toContain('target_date')
  })

  it('fails before requesting when the public API base URL is missing', async () => {
    const request = vi.fn()
    const api = createTechnicalDebtApi({ apiBaseUrl: '   ', request })

    await expect(api.listTechnicalDebts()).rejects.toBeInstanceOf(
      TechnicalDebtApiConfigurationError,
    )
    await expect(api.getTechnicalDebt(TECHNICAL_DEBT_ID)).rejects.toThrow(
      'Public API base URL is not configured',
    )
    expect(request).not.toHaveBeenCalled()
  })

  it('does not convert HTTP failures into successful empty data', async () => {
    const notFound = httpError(404, 'TechnicalDebt not found')
    const malformed = httpError(422, 'Invalid technical_debt_id')

    await expect(
      createTechnicalDebtApi({
        apiBaseUrl: API_ORIGIN,
        request: vi.fn().mockRejectedValue(notFound),
      }).getTechnicalDebt(TECHNICAL_DEBT_ID),
    ).rejects.toBe(notFound)

    await expect(
      createTechnicalDebtApi({
        apiBaseUrl: API_ORIGIN,
        request: vi.fn().mockRejectedValue(malformed),
      }).getTechnicalDebt('not-a-uuid'),
    ).rejects.toMatchObject({ statusCode: 422 })
  })

  it('posts to the ActionProposal preparation endpoint without a client body', async () => {
    const proposal: ActionProposal = {
      action_proposal_id: '60000000-0000-0000-0000-000000000001',
      technical_debt_id: TECHNICAL_DEBT_ID,
      action_type: 'CREATE_GITHUB_ISSUE',
      target_repository_owner: 'tdi-demo-target',
      target_repository_name: 'tdi-action-preview',
      title: 'Technical debt: svc-orbit-catalog',
      body: 'Technical debt remediation tracking issue',
      payload_fingerprint: 'abc123',
      reconciliation_marker: 'tdiq-action-proposal:60000000-0000-0000-0000-000000000001',
      prepared_by: 'poc:local-reviewer',
      created_at: '2026-09-07T16:00:00+00:00',
    }
    const request = vi.fn().mockResolvedValue(proposal)
    const api = createTechnicalDebtApi({ apiBaseUrl: API_ORIGIN, request })

    const result = await api.prepareActionProposal(TECHNICAL_DEBT_ID)

    expect(request).toHaveBeenCalledTimes(1)
    expect(request).toHaveBeenCalledWith(
      `${API_ORIGIN}/api/v1/technical-debts/${TECHNICAL_DEBT_ID}/action-proposals`,
      { method: 'POST' },
    )
    expect(request.mock.calls[0]?.[1]).not.toHaveProperty('body')
    expect(result).toBe(proposal)
    expect(result).not.toHaveProperty('approval')
    expect(result).not.toHaveProperty('execution')
    expect(result).not.toHaveProperty('verification')
  })

  it('does not convert ActionProposal HTTP failures into a successful prepare', async () => {
    const unavailable = httpError(503, 'Action preparation is unavailable because the server is not configured')

    await expect(
      createTechnicalDebtApi({
        apiBaseUrl: API_ORIGIN,
        request: vi.fn().mockRejectedValue(unavailable),
      }).prepareActionProposal(TECHNICAL_DEBT_ID),
    ).rejects.toBe(unavailable)
  })

  it('posts approval intent with only the persisted payload fingerprint', async () => {
    const approval: ActionApproval = {
      action_approval_id: '70000000-0000-0000-0000-000000000001',
      action_proposal_id: '60000000-0000-0000-0000-000000000001',
      payload_fingerprint: 'a'.repeat(64),
      actor_reference: 'poc:server-owned-actor',
      created_at: '2026-09-07T16:01:00+00:00',
    }
    const request = vi.fn().mockResolvedValue(approval)
    const api = createTechnicalDebtApi({ apiBaseUrl: API_ORIGIN, request })

    await api.approveActionProposal(
      TECHNICAL_DEBT_ID,
      approval.action_proposal_id,
      { expected_payload_fingerprint: approval.payload_fingerprint },
    )

    expect(request).toHaveBeenCalledTimes(1)
    expect(request.mock.calls[0]?.[1]).toEqual({
      method: 'POST',
      body: { expected_payload_fingerprint: approval.payload_fingerprint },
    })
    expect(request.mock.calls[0]?.[1]?.body).not.toHaveProperty('actor')
    expect(request.mock.calls[0]?.[1]?.body).not.toHaveProperty('approved')
    expect(request.mock.calls[0]?.[1]?.body).not.toHaveProperty('repository')
    expect(request.mock.calls[0]?.[1]?.body).not.toHaveProperty('policy_decision')
  })

  it('posts execution and verification without bodies', async () => {
    const proposalId = '60000000-0000-0000-0000-000000000001'
    const execution: ActionExecution = {
      action_execution_id: '80000000-0000-0000-0000-000000000001',
      action_proposal_id: proposalId,
      technical_debt_id: TECHNICAL_DEBT_ID,
      action_type: 'CREATE_GITHUB_ISSUE',
      creation_policy_decision_id: '81000000-0000-0000-0000-000000000001',
      status: 'SUCCEEDED',
      external_issue_id: 123,
      external_issue_number: 42,
      external_issue_url: 'https://github.example.test/exact/persisted/issues/42',
      safe_error_category: null,
      started_at: '2026-09-07T16:02:00+00:00',
      completed_at: '2026-09-07T16:02:01+00:00',
    }
    const verification: ActionVerification = {
      action_verification_id: '90000000-0000-0000-0000-000000000001',
      action_execution_id: execution.action_execution_id,
      result: 'PASS',
      observed_issue_number: 42,
      observed_issue_url: execution.external_issue_url,
      safe_reason_code: null,
      created_at: '2026-09-07T16:03:00+00:00',
    }
    const request = vi.fn().mockResolvedValueOnce(execution).mockResolvedValueOnce(verification)
    const api = createTechnicalDebtApi({ apiBaseUrl: API_ORIGIN, request })

    await api.executeActionProposal(TECHNICAL_DEBT_ID, proposalId)
    await api.verifyActionExecution(
      TECHNICAL_DEBT_ID,
      proposalId,
      execution.action_execution_id,
    )

    expect(request).toHaveBeenCalledTimes(2)
    expect(request.mock.calls[0]?.[1]).toEqual({ method: 'POST' })
    expect(request.mock.calls[1]?.[1]).toEqual({ method: 'POST' })
    expect(request.mock.calls[0]?.[1]).not.toHaveProperty('body')
    expect(request.mock.calls[1]?.[1]).not.toHaveProperty('body')
  })
})
