import { describe, expect, it, vi } from 'vitest'
import {
  TechnicalDebtApiConfigurationError,
  createTechnicalDebtApi,
} from '../../app/composables/useTechnicalDebtApi'
import type {
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
})
