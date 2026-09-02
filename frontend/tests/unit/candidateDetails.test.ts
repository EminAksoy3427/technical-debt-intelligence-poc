import { describe, expect, it } from 'vitest'
import { getMockCandidateDetail } from '../../app/mocks/candidateDetails'

describe('Candidate Detail controlled mock', () => {
  it('returns the matching detail for a known Candidate ID', () => {
    expect(getMockCandidateDetail('CND-101')).toMatchObject({
      id: 'CND-101',
      title: 'Duplicate approval rules across submission paths',
      reviewStatus: 'awaiting_review',
    })
  })

  it('returns no detail for an unknown Candidate ID', () => {
    expect(getMockCandidateDetail('CND-999')).toBeUndefined()
  })

  it('keeps multiple evidence items for CND-101', () => {
    expect(getMockCandidateDetail('CND-101')?.evidence.length).toBeGreaterThan(1)
  })
})
