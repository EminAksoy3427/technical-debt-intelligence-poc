import { describe, expect, it } from 'vitest'
import { mockCandidates } from '../../app/mocks/candidates'
import { filterCandidates } from '../../app/utils/filterCandidates'

describe('filterCandidates', () => {
  it('returns all candidates when filters are empty', () => {
    expect(filterCandidates(mockCandidates, {})).toEqual(mockCandidates)
  })

  it('searches case-insensitively', () => {
    expect(filterCandidates(mockCandidates, { search: 'NORTHSTAR' })).toHaveLength(1)
  })

  it('searches candidate titles', () => {
    expect(filterCandidates(mockCandidates, { search: 'translation' })[0]?.id).toBe('CND-105')
  })

  it('searches affected asset names', () => {
    expect(filterCandidates(mockCandidates, { search: 'willow' })[0]?.id).toBe('CND-104')
  })

  it('filters by review status', () => {
    expect(
      filterCandidates(mockCandidates, { reviewStatus: 'needs_information' }).map(
        (candidate) => candidate.id,
      ),
    ).toEqual(['CND-102', 'CND-104', 'CND-106'])
  })

  it('filters by asset type', () => {
    expect(
      filterCandidates(mockCandidates, { assetType: 'service' }).map((candidate) => candidate.id),
    ).toEqual(['CND-103', 'CND-105'])
  })

  it('combines active filters', () => {
    expect(
      filterCandidates(mockCandidates, {
        search: 'archive',
        reviewStatus: 'needs_information',
        assetType: 'data_store',
      }).map((candidate) => candidate.id),
    ).toEqual(['CND-104'])
  })

  it('returns an empty collection when no candidates match', () => {
    expect(filterCandidates(mockCandidates, { search: 'unmatched value' })).toEqual([])
  })
})
