import { describe, expect, it } from 'vitest'
import type { CandidateListItem } from '../../app/types/candidate'
import {
  areCandidateFiltersActive,
  filterCandidates,
} from '../../app/utils/filterCandidates'

const CANDIDATE_APPLICATION_ID = '20000000-0000-0000-0000-000000000001'
const CANDIDATE_SERVICE_ID = '20000000-0000-0000-0000-000000000002'
const CANDIDATE_REPOSITORY_ID = '20000000-0000-0000-0000-000000000003'
const CANDIDATE_TIMEOUT_ID = '20000000-0000-0000-0000-000000000004'

const candidates: CandidateListItem[] = [
  {
    id: CANDIDATE_APPLICATION_ID,
    title: 'Potential missing request timeout',
    presentationTitle: 'Potential missing request timeout',
    assetName: 'Harbor Intake',
    assetType: 'APPLICATION',
    signalCount: 3,
    evidenceCount: 4,
  },
  {
    id: CANDIDATE_SERVICE_ID,
    title: 'Repeated exception handling in document intake',
    presentationTitle: 'Repeated exception handling in document intake',
    assetName: 'Orbit Catalog',
    assetType: 'SERVICE',
    signalCount: 2,
    evidenceCount: 2,
  },
  {
    id: CANDIDATE_REPOSITORY_ID,
    title: 'Inconsistent retention checks for archived records',
    presentationTitle: 'Inconsistent retention checks for archived records',
    assetName: 'Willow Archive',
    assetType: 'REPOSITORY',
    signalCount: 1,
    evidenceCount: 1,
  },
  {
    id: CANDIDATE_TIMEOUT_ID,
    title: 'Potential MISSING_TIMEOUT issue affecting svc-orbit-catalog',
    presentationTitle: 'Missing network timeout',
    assetName: 'Orbit Catalog API',
    assetType: 'SERVICE',
    signalCount: 2,
    evidenceCount: 3,
  },
]

describe('filterCandidates', () => {
  it('returns all candidates when filters are empty', () => {
    expect(filterCandidates(candidates, {})).toEqual(candidates)
  })

  it('searches hypotheses case-insensitively', () => {
    expect(filterCandidates(candidates, { search: 'TIMEOUT' }).map((candidate) => candidate.id)).toEqual([
      CANDIDATE_APPLICATION_ID,
      CANDIDATE_TIMEOUT_ID,
    ])
  })

  it('searches human-readable presentation titles', () => {
    expect(
      filterCandidates(candidates, { search: 'Missing network' }).map((candidate) => candidate.id),
    ).toEqual([CANDIDATE_TIMEOUT_ID])
  })

  it('searches enterprise asset names case-insensitively', () => {
    expect(filterCandidates(candidates, { search: 'willow' }).map((candidate) => candidate.id)).toEqual([
      CANDIDATE_REPOSITORY_ID,
    ])
  })

  it('filters by APPLICATION, SERVICE, and REPOSITORY', () => {
    expect(
      filterCandidates(candidates, { assetType: 'APPLICATION' }).map((candidate) => candidate.id),
    ).toEqual([CANDIDATE_APPLICATION_ID])
    expect(
      filterCandidates(candidates, { assetType: 'SERVICE' }).map((candidate) => candidate.id),
    ).toEqual([CANDIDATE_SERVICE_ID, CANDIDATE_TIMEOUT_ID])
    expect(
      filterCandidates(candidates, { assetType: 'REPOSITORY' }).map((candidate) => candidate.id),
    ).toEqual([CANDIDATE_REPOSITORY_ID])
  })

  it('combines search with asset type', () => {
    expect(
      filterCandidates(candidates, {
        search: 'archive',
        assetType: 'REPOSITORY',
      }).map((candidate) => candidate.id),
    ).toEqual([CANDIDATE_REPOSITORY_ID])

    expect(
      filterCandidates(candidates, {
        search: 'archive',
        assetType: 'APPLICATION',
      }),
    ).toEqual([])
  })

  it('does not filter by review status', () => {
    expect(filterCandidates(candidates, { search: 'timeout' }).map((candidate) => candidate.id)).toEqual([
      CANDIDATE_APPLICATION_ID,
      CANDIDATE_TIMEOUT_ID,
    ])
    expect(filterCandidates(candidates, {})).toHaveLength(candidates.length)
    expect(filterCandidates(candidates, { assetType: 'SERVICE' })[0]).not.toHaveProperty('reviewStatus')
  })

  it('does not treat data_store as a pool asset type', () => {
    expect(candidates.map((candidate) => candidate.assetType)).toEqual([
      'APPLICATION',
      'SERVICE',
      'REPOSITORY',
      'SERVICE',
    ])
    expect(candidates.some((candidate) => String(candidate.assetType).toLowerCase() === 'data_store')).toBe(
      false,
    )
  })

  it('preserves UUID Candidate identity', () => {
    expect(filterCandidates(candidates, { assetType: 'APPLICATION' })[0]?.id).toBe(
      CANDIDATE_APPLICATION_ID,
    )
    expect(filterCandidates(candidates, { assetType: 'APPLICATION' })[0]?.id).not.toMatch(/^CND-/)
  })

  it('returns an empty collection when no candidates match', () => {
    expect(filterCandidates(candidates, { search: 'unmatched value' })).toEqual([])
  })
})

describe('areCandidateFiltersActive', () => {
  it('is inactive when search and asset type are empty', () => {
    expect(areCandidateFiltersActive({})).toBe(false)
    expect(areCandidateFiltersActive({ search: '   ', assetType: '' })).toBe(false)
  })

  it('is active when search or asset type is set', () => {
    expect(areCandidateFiltersActive({ search: 'timeout' })).toBe(true)
    expect(areCandidateFiltersActive({ assetType: 'SERVICE' })).toBe(true)
    expect(areCandidateFiltersActive({ search: 'orbit', assetType: 'SERVICE' })).toBe(true)
  })
})
