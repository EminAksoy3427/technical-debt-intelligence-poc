import { describe, expect, it } from 'vitest'
import { resolveOverviewCandidateViewState } from '../../app/utils/resolveOverviewCandidateViewState'

describe('resolveOverviewCandidateViewState', () => {
  it('returns loading while the list request is in progress', () => {
    expect(
      resolveOverviewCandidateViewState({
        pending: true,
        hasError: false,
        hasListResponse: false,
        candidateCount: 0,
      }),
    ).toBe('loading')
  })

  it('returns error when the Candidate list cannot be loaded', () => {
    expect(
      resolveOverviewCandidateViewState({
        pending: false,
        hasError: true,
        hasListResponse: false,
        candidateCount: 0,
      }),
    ).toBe('error')
  })

  it('returns empty when the backend successfully returns zero Candidates', () => {
    expect(
      resolveOverviewCandidateViewState({
        pending: false,
        hasError: false,
        hasListResponse: true,
        candidateCount: 0,
      }),
    ).toBe('empty')
  })

  it('returns ready when Candidates are available', () => {
    expect(
      resolveOverviewCandidateViewState({
        pending: false,
        hasError: false,
        hasListResponse: true,
        candidateCount: 4,
      }),
    ).toBe('ready')
  })
})
