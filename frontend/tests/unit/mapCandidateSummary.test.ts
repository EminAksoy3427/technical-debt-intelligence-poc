import { describe, expect, it } from 'vitest'
import {
  candidateAssetTypeDisplayLabel,
} from '../../app/types/candidate'
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
      presentationTitle: 'Potential missing request timeout',
      assetName: 'Orbit Catalog',
      assetType: 'SERVICE',
      signalCount: 2,
      evidenceCount: 3,
    })
  })

  it('maps known hypothesis templates to a human-readable Candidate title', () => {
    const item = toCandidateListItem({
      ...summary,
      hypothesis: 'Potential MISSING_TIMEOUT issue affecting svc-orbit-catalog',
    })

    expect(item.presentationTitle).toBe('Missing network timeout')
    expect(item.title).toBe('Potential MISSING_TIMEOUT issue affecting svc-orbit-catalog')
    expect(item.id).toBe(CANDIDATE_ID)
  })

  it('falls back to the hypothesis when no safe presentation title exists', () => {
    const item = toCandidateListItem({
      ...summary,
      hypothesis: 'Potential UNKNOWN_FAMILY issue affecting repo-x',
    })

    expect(item.presentationTitle).toBe('Potential UNKNOWN_FAMILY issue affecting repo-x')
  })

  it('falls back to the canonical asset key when the enterprise name is blank', () => {
    const item = toCandidateListItem({
      ...summary,
      enterprise_asset: {
        ...summary.enterprise_asset,
        name: '   ',
      },
    })

    expect(item.assetName).toBe('svc-orbit-catalog')
  })

  it('uses the Candidate UUID rather than a CND alias', () => {
    const item = toCandidateListItem(summary)

    expect(item.id).toBe(summary.candidate_id)
    expect(item.id).not.toMatch(/^CND-/)
    expect(item.presentationTitle).not.toBe(item.id)
    expect(item.title).not.toBe(item.id)
  })

  it('does not invent governance, source, or scoring fields', () => {
    const item = toCandidateListItem(summary)

    expect(item).not.toHaveProperty('reviewStatus')
    expect(item).not.toHaveProperty('governanceState')
    expect(item).not.toHaveProperty('sourceSystem')
    expect(item).not.toHaveProperty('suggestedTeam')
    expect(item).not.toHaveProperty('risk')
    expect(item).not.toHaveProperty('effort')
    expect(item).not.toHaveProperty('priority')
    expect(item).not.toHaveProperty('confidence')
    expect(item).not.toHaveProperty('technicalDebtId')
  })
})

describe('candidateAssetTypeDisplayLabel', () => {
  it('maps known asset types and keeps unknown values as-is', () => {
    expect(candidateAssetTypeDisplayLabel('APPLICATION')).toBe('Application')
    expect(candidateAssetTypeDisplayLabel('SERVICE')).toBe('Service')
    expect(candidateAssetTypeDisplayLabel('REPOSITORY')).toBe('Repository')
    expect(candidateAssetTypeDisplayLabel('WIDGET')).toBe('WIDGET')
  })
})
