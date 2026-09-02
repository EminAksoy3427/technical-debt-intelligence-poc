import { describe, expect, it } from 'vitest'
import type { CandidateDetailResponse } from '../../app/types/candidateApi'
import {
  resolveCandidateDetailErrorState,
  resolveCandidateDetailViewState,
} from '../../app/utils/resolveCandidateDetailViewState'

const CANDIDATE_ID = '20000000-0000-0000-0000-000000000001'
const OTHER_CANDIDATE_ID = '20000000-0000-0000-0000-000000000002'

const detail = {
  candidate: { candidate_id: CANDIDATE_ID },
} as CandidateDetailResponse

describe('resolveCandidateDetailErrorState', () => {
  it('resolves HTTP 404 to not-found without using the error message', () => {
    expect(resolveCandidateDetailErrorState({ statusCode: 404, message: 'other text' })).toBe(
      'not-found',
    )
  })

  it('resolves HTTP 422 to invalid-identifier', () => {
    expect(resolveCandidateDetailErrorState({ statusCode: 422 })).toBe('invalid-identifier')
    expect(resolveCandidateDetailErrorState({ status: 422 })).toBe('invalid-identifier')
  })

  it('resolves HTTP 500 to generic error', () => {
    expect(resolveCandidateDetailErrorState({ statusCode: 500 })).toBe('error')
  })

  it('resolves a network error with no HTTP status to generic error', () => {
    expect(resolveCandidateDetailErrorState(new Error('fetch failed'))).toBe('error')
    expect(resolveCandidateDetailErrorState({ message: 'network' })).toBe('error')
  })
})

describe('resolveCandidateDetailViewState', () => {
  it('returns loading while the Detail request is in progress', () => {
    expect(
      resolveCandidateDetailViewState({
        pending: true,
        error: null,
        detail: undefined,
        requestedCandidateId: CANDIDATE_ID,
      }),
    ).toBe('loading')
  })

  it('does not present stale Candidate data for a different route ID', () => {
    expect(
      resolveCandidateDetailViewState({
        pending: false,
        error: null,
        detail,
        requestedCandidateId: OTHER_CANDIDATE_ID,
      }),
    ).toBe('loading')
  })

  it('returns success only when the response Candidate ID matches the route', () => {
    expect(
      resolveCandidateDetailViewState({
        pending: false,
        error: null,
        detail,
        requestedCandidateId: CANDIDATE_ID,
      }),
    ).toBe('success')
  })

  it('does not convert API failure into a successful Detail', () => {
    expect(
      resolveCandidateDetailViewState({
        pending: false,
        error: { statusCode: 500 },
        detail: undefined,
        requestedCandidateId: CANDIDATE_ID,
      }),
    ).toBe('error')

    expect(
      resolveCandidateDetailViewState({
        pending: false,
        error: { statusCode: 404 },
        detail,
        requestedCandidateId: CANDIDATE_ID,
      }),
    ).toBe('not-found')
  })

  it('keeps loading ahead of a previous error while a new request is pending', () => {
    expect(
      resolveCandidateDetailViewState({
        pending: true,
        error: { statusCode: 404 },
        detail: undefined,
        requestedCandidateId: CANDIDATE_ID,
      }),
    ).toBe('loading')
  })
})
