import { describe, expect, it, vi } from 'vitest'
import {
  CandidateApiConfigurationError,
  createCandidateApi,
} from '../../app/composables/useCandidateApi'
import type {
  CandidateDetailResponse,
  CandidateListResponse,
} from '../../app/types/candidateApi'

const API_ORIGIN = 'https://candidate-api.example.test'
const CANDIDATE_ID = '20000000-0000-0000-0000-000000000001'

const listPayload: CandidateListResponse = {
  items: [
    {
      candidate_id: CANDIDATE_ID,
      hypothesis: 'Potential missing request timeout',
      canonical_asset: {
        asset_key: 'svc-orbit-catalog',
        asset_type: 'SERVICE',
      },
      enterprise_asset: {
        asset_key: 'svc-orbit-catalog',
        asset_type: 'SERVICE',
        name: 'Orbit Catalog',
        criticality: 'HIGH',
        lifecycle_status: 'ACTIVE',
      },
      signal_count: 2,
      evidence_count: 2,
    },
  ],
  count: 1,
}

const detailPayload: CandidateDetailResponse = {
  candidate: {
    candidate_id: CANDIDATE_ID,
    signal_ids: ['00000000-0000-0000-0000-000000000011'],
    evidence_ids: ['10000000-0000-0000-0000-000000000011'],
    canonical_asset: {
      asset_key: 'svc-orbit-catalog',
      asset_type: 'SERVICE',
    },
    hypothesis: 'Potential missing request timeout',
    correlation_rationale: 'Exact canonical asset and deterministic problem family.',
  },
  signals: [
    {
      signal_id: '00000000-0000-0000-0000-000000000011',
      source_system: 'candidate-api-test',
      source_record_id: 'member-earlier',
      detected_at: '2026-08-31T10:00:00+00:00',
      signal_type: 'MISSING_TIMEOUT',
      affected_asset: {
        asset_key: 'svc-orbit-catalog',
        asset_type: 'SERVICE',
      },
      severity: 'MEDIUM',
      evidence_ids: ['10000000-0000-0000-0000-000000000011'],
    },
  ],
  evidence: [
    {
      evidence_id: '10000000-0000-0000-0000-000000000011',
      source_system: 'candidate-api-test',
      source_reference: 'evidence:member-earlier',
      captured_at: '2026-08-31T10:01:00+00:00',
      reference_uri: 'https://synthetic.invalid/member-earlier',
    },
  ],
  enterprise_context: {
    candidate_id: CANDIDATE_ID,
    enterprise_asset: {
      asset_key: 'svc-orbit-catalog',
      asset_type: 'SERVICE',
      name: 'Orbit Catalog',
      criticality: 'HIGH',
      lifecycle_status: 'ACTIVE',
    },
    enterprise_ownerships: [
      {
        asset_ownership: {
          asset_key: 'svc-orbit-catalog',
          team_key: 'team-orbit',
          ownership_role: 'PRIMARY',
        },
        team: { team_key: 'team-orbit', name: 'Orbit Platform Team' },
      },
    ],
    direct_relationships: [
      {
        source_asset_key: 'app-orbit',
        target_asset_key: 'svc-orbit-catalog',
        relationship_type: 'IMPLEMENTED_BY',
      },
    ],
    direct_incidents: [
      {
        incident_key: 'inc-orbit-001',
        primary_affected_asset_key: 'svc-orbit-catalog',
        severity: 'HIGH',
        title: 'Catalog timeouts',
        started_at: '2026-08-01T08:00:00+00:00',
        resolved_at: null,
      },
    ],
  },
  dependency_context: {
    candidate_id: CANDIDATE_ID,
    candidate_asset: {
      asset_key: 'svc-orbit-catalog',
      asset_type: 'SERVICE',
    },
    dependency_anchors: [
      {
        asset_key: 'svc-orbit-catalog',
        asset_type: 'SERVICE',
      },
    ],
    direct_dependencies: [],
    direct_dependents: [
      {
        asset_key: 'svc-asteria-editor',
        asset_type: 'SERVICE',
      },
    ],
    reachable_dependents: [
      {
        asset_key: 'svc-asteria-editor',
        asset_type: 'SERVICE',
      },
    ],
  },
  governance: {
    state: 'PENDING',
    revision: 0,
    decisions: [],
    technical_debt: null,
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

describe('createCandidateApi', () => {
  it('calls the Candidate list endpoint with the configured API base URL', async () => {
    const request = vi.fn().mockResolvedValue(listPayload)
    const api = createCandidateApi({ apiBaseUrl: API_ORIGIN, request })

    const result = await api.getCandidates()

    expect(request).toHaveBeenCalledWith(`${API_ORIGIN}/api/v1/candidates`)
    expect(result).toBe(listPayload)
  })

  it('calls the Candidate detail endpoint with the Candidate UUID', async () => {
    const request = vi.fn().mockResolvedValue(detailPayload)
    const api = createCandidateApi({ apiBaseUrl: API_ORIGIN, request })

    const result = await api.getCandidate(CANDIDATE_ID)

    expect(request).toHaveBeenCalledWith(`${API_ORIGIN}/api/v1/candidates/${CANDIDATE_ID}`)
    expect(result).toBe(detailPayload)
  })

  it('does not introduce a duplicate slash when the API base URL has a trailing slash', async () => {
    const request = vi.fn().mockResolvedValue(listPayload)
    const api = createCandidateApi({ apiBaseUrl: `${API_ORIGIN}/`, request })

    await api.getCandidates()

    expect(request).toHaveBeenCalledWith(`${API_ORIGIN}/api/v1/candidates`)
  })

  it('returns the wire JSON without presentation or governance mapping', async () => {
    const request = vi.fn().mockResolvedValue(listPayload)
    const api = createCandidateApi({ apiBaseUrl: API_ORIGIN, request })

    const result = await api.getCandidates()
    const item = result.items[0]

    expect(item).toEqual(listPayload.items[0])
    expect(item).toHaveProperty('candidate_id', CANDIDATE_ID)
    expect(item).toHaveProperty('signal_count', 2)
    expect(item).toHaveProperty('enterprise_asset')
    expect(item).not.toHaveProperty('id')
    expect(item).not.toHaveProperty('title')
    expect(item).not.toHaveProperty('reviewStatus')
    expect(item).not.toHaveProperty('suggestedTeam')
    expect(item).not.toHaveProperty('risk')
    expect(item).not.toHaveProperty('priority')
    expect(item).not.toHaveProperty('confidence')
  })

  it('fails before requesting when the public API base URL is missing', async () => {
    const request = vi.fn()
    const api = createCandidateApi({ apiBaseUrl: '', request })

    await expect(api.getCandidates()).rejects.toBeInstanceOf(CandidateApiConfigurationError)
    await expect(api.getCandidates()).rejects.toThrow('Public API base URL is not configured')
    expect(request).not.toHaveBeenCalled()
  })

  it('fails before requesting when the public API base URL is blank', async () => {
    const request = vi.fn()
    const api = createCandidateApi({ apiBaseUrl: '   ', request })

    await expect(api.getCandidate(CANDIDATE_ID)).rejects.toThrow(
      'Public API base URL is not configured',
    )
    expect(request).not.toHaveBeenCalled()
  })

  it('does not convert HTTP failures into successful empty data', async () => {
    const notFound = httpError(404, 'Candidate not found')
    const malformed = httpError(422, 'Invalid candidate_id')
    const integrityFailure = httpError(
      500,
      'Persisted Candidate data failed integrity validation',
    )

    const notFoundRequest = vi.fn().mockRejectedValue(notFound)
    await expect(
      createCandidateApi({ apiBaseUrl: API_ORIGIN, request: notFoundRequest }).getCandidate(
        CANDIDATE_ID,
      ),
    ).rejects.toBe(notFound)

    const malformedRequest = vi.fn().mockRejectedValue(malformed)
    await expect(
      createCandidateApi({
        apiBaseUrl: API_ORIGIN,
        request: malformedRequest,
      }).getCandidate('not-a-uuid'),
    ).rejects.toMatchObject({ statusCode: 422 })

    const integrityRequest = vi.fn().mockRejectedValue(integrityFailure)
    await expect(
      createCandidateApi({ apiBaseUrl: API_ORIGIN, request: integrityRequest }).getCandidates(),
    ).rejects.toMatchObject({ statusCode: 500, data: { detail: integrityFailure.data.detail } })
  })
})
