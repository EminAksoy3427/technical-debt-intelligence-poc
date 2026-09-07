import { describe, expect, it } from 'vitest'
import {
  OVERVIEW_CANDIDATES_FOR_REVIEW_LIMIT,
  selectCandidatesForReview,
} from '../../app/utils/selectCandidatesForReview'

describe('selectCandidatesForReview', () => {
  it('preserves list order and does not invent recency or priority sorting', () => {
    const candidates = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth']

    expect(selectCandidatesForReview(candidates)).toEqual([
      'first',
      'second',
      'third',
      'fourth',
      'fifth',
    ])
    expect(OVERVIEW_CANDIDATES_FOR_REVIEW_LIMIT).toBe(5)
  })

  it('returns the full collection when it is smaller than the display limit', () => {
    expect(selectCandidatesForReview(['only'])).toEqual(['only'])
    expect(selectCandidatesForReview([])).toEqual([])
  })
})
