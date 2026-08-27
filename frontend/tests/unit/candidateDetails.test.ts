import { describe, expect, it } from 'vitest'
import { getMockCandidateDetail, mockCandidateDetails } from '../../app/mocks/candidateDetails'
import { mockCandidates } from '../../app/mocks/candidates'

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

  it('provides one detail record for every Candidate Pool item', () => {
    expect(mockCandidateDetails.map((candidate) => candidate.id).sort()).toEqual(
      mockCandidates.map((candidate) => candidate.id).sort(),
    )
  })

  it('keeps review status, suggested team, and evidence counts consistent with the Candidate Pool', () => {
    for (const candidate of mockCandidates) {
      const detail = getMockCandidateDetail(candidate.id)

      expect(detail).toBeDefined()
      expect(detail?.reviewStatus).toBe(candidate.reviewStatus)
      expect(detail?.suggestedTeam).toBe(candidate.suggestedTeam)
      expect(detail?.evidence).toHaveLength(candidate.evidenceItemCount)
    }
  })

  it('keeps multiple evidence items for CND-101', () => {
    expect(getMockCandidateDetail('CND-101')?.evidence.length).toBeGreaterThan(1)
  })
})
