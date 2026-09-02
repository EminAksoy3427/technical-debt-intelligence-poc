import { describe, expect, it } from 'vitest'
import type { CandidateSummaryResponse } from '../../app/types/candidateApi'
import { toCandidateListItem } from '../../app/utils/mapCandidateSummary'

const CANDIDATE_ID = '20000000-0000-0000-0000-000000000001'

const summary: CandidateSummaryResponse = {
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
  evidence_count: 3,
}

describe('toCandidateListItem', () => {
  it('maps list API fields onto the Candidate Pool presentation model', () => {
    expect(toCandidateListItem(summary)).toEqual({
      id: CANDIDATE_ID,
      title: 'Potential missing request timeout',
      assetName: 'Orbit Catalog',
      assetType: 'SERVICE',
      signalCount: 2,
      evidenceCount: 3,
    })
  })

  it('uses the Candidate UUID rather than a CND alias', () => {
    const item = toCandidateListItem(summary)

    expect(item.id).toBe(summary.candidate_id)
    expect(item.id).not.toMatch(/^CND-/)
  })

  it('does not invent governance or scoring fields', () => {
    const item = toCandidateListItem(summary)

    expect(item).not.toHaveProperty('reviewStatus')
    expect(item).not.toHaveProperty('suggestedTeam')
    expect(item).not.toHaveProperty('risk')
    expect(item).not.toHaveProperty('effort')
    expect(item).not.toHaveProperty('priority')
    expect(item).not.toHaveProperty('confidence')
  })
})
