import { describe, expect, it } from 'vitest'
import type { CandidateListItem } from '../../app/types/candidate'
import { summarizeCandidateCollection } from '../../app/utils/summarizeCandidateCollection'

function candidate(overrides: Partial<CandidateListItem> = {}): CandidateListItem {
  return {
    id: '20000000-0000-0000-0000-000000000001',
    title: 'Potential MISSING_TIMEOUT issue affecting svc-orbit-catalog',
    presentationTitle: 'Missing network timeout',
    assetName: 'Orbit Catalog',
    assetType: 'SERVICE',
    signalCount: 1,
    evidenceCount: 1,
    ...overrides,
  }
}

describe('summarizeCandidateCollection', () => {
  it('derives Candidate count from the list length', () => {
    const summary = summarizeCandidateCollection([
      candidate({ id: '1' }),
      candidate({ id: '2' }),
    ])

    expect(summary.candidateCount).toBe(2)
  })

  it('sums signal_count values only for signals represented', () => {
    const summary = summarizeCandidateCollection([
      candidate({ id: '1', signalCount: 1, evidenceCount: 4 }),
      candidate({ id: '2', signalCount: 3, evidenceCount: 9 }),
    ])

    expect(summary.signalsRepresented).toBe(4)
    expect(summary.evidenceRepresented).toBe(13)
  })

  it('lists distinct asset types from the Candidate collection', () => {
    const summary = summarizeCandidateCollection([
      candidate({ id: '1', assetType: 'REPOSITORY' }),
      candidate({ id: '2', assetType: 'SERVICE' }),
      candidate({ id: '3', assetType: 'SERVICE' }),
      candidate({ id: '4', assetType: 'APPLICATION' }),
    ])

    expect(summary.assetTypesRepresented).toEqual([
      { assetType: 'APPLICATION', label: 'Application' },
      { assetType: 'SERVICE', label: 'Service' },
      { assetType: 'REPOSITORY', label: 'Repository' },
    ])
  })

  it('returns zeros and no asset types for an empty collection', () => {
    expect(summarizeCandidateCollection([])).toEqual({
      candidateCount: 0,
      signalsRepresented: 0,
      evidenceRepresented: 0,
      assetTypesRepresented: [],
    })
  })

  it('does not invent governance, risk, or scoring aggregates', () => {
    const summary = summarizeCandidateCollection([candidate()])

    expect(summary).not.toHaveProperty('validatedCount')
    expect(summary).not.toHaveProperty('pendingCount')
    expect(summary).not.toHaveProperty('rejectedCount')
    expect(summary).not.toHaveProperty('risk')
    expect(summary).not.toHaveProperty('severity')
    expect(summary).not.toHaveProperty('priority')
    expect(summary).not.toHaveProperty('coverage')
    expect(summary).not.toHaveProperty('confidence')
  })
})
