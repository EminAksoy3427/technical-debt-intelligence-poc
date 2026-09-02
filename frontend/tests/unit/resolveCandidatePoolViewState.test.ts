import { describe, expect, it } from 'vitest'
import { resolveCandidatePoolViewState } from '../../app/utils/resolveCandidatePoolViewState'

describe('resolveCandidatePoolViewState', () => {
  it('returns loading while the list request is in progress', () => {
    expect(
      resolveCandidatePoolViewState({
        pending: true,
        hasError: false,
        hasListResponse: false,
        candidateCount: 0,
        filteredCount: 0,
      }),
    ).toBe('loading')
  })

  it('does not treat an API failure as a successful empty list', () => {
    expect(
      resolveCandidatePoolViewState({
        pending: false,
        hasError: true,
        hasListResponse: false,
        candidateCount: 0,
        filteredCount: 0,
      }),
    ).toBe('error')
  })

  it('returns empty when the backend successfully returns zero Candidates', () => {
    expect(
      resolveCandidatePoolViewState({
        pending: false,
        hasError: false,
        hasListResponse: true,
        candidateCount: 0,
        filteredCount: 0,
      }),
    ).toBe('empty')
  })

  it('returns filtered-empty when Candidates exist but none match the current filters', () => {
    expect(
      resolveCandidatePoolViewState({
        pending: false,
        hasError: false,
        hasListResponse: true,
        candidateCount: 3,
        filteredCount: 0,
      }),
    ).toBe('filtered-empty')
  })

  it('returns ready when filtered Candidates are available', () => {
    expect(
      resolveCandidatePoolViewState({
        pending: false,
        hasError: false,
        hasListResponse: true,
        candidateCount: 3,
        filteredCount: 2,
      }),
    ).toBe('ready')
  })
})
