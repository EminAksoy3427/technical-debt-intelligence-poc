import { describe, expect, it } from 'vitest'
import {
  resolveAgentInvestigationRequestError,
  resolveAgentInvestigationViewState,
} from '../../app/utils/resolveAgentInvestigationViewState'

describe('resolveAgentInvestigationViewState', () => {
  it('returns idle when no request is active and no run is present', () => {
    expect(
      resolveAgentInvestigationViewState({
        requestState: 'idle',
        runStatus: null,
      }),
    ).toBe('idle')
  })

  it('returns starting while the POST request is active', () => {
    expect(
      resolveAgentInvestigationViewState({
        requestState: 'starting',
        runStatus: null,
      }),
    ).toBe('starting')

    expect(
      resolveAgentInvestigationViewState({
        requestState: 'starting',
        runStatus: 'COMPLETED',
      }),
    ).toBe('starting')
  })

  it('returns request-error for a failed request without renaming the run', () => {
    expect(
      resolveAgentInvestigationViewState({
        requestState: 'error',
        runStatus: null,
      }),
    ).toBe('request-error')
  })

  it('maps persisted runtime statuses without renaming them', () => {
    expect(
      resolveAgentInvestigationViewState({ requestState: 'idle', runStatus: 'CREATED' }),
    ).toBe('created')
    expect(
      resolveAgentInvestigationViewState({ requestState: 'idle', runStatus: 'RUNNING' }),
    ).toBe('running')
    expect(
      resolveAgentInvestigationViewState({ requestState: 'idle', runStatus: 'COMPLETED' }),
    ).toBe('completed')
    expect(
      resolveAgentInvestigationViewState({ requestState: 'idle', runStatus: 'ABSTAINED' }),
    ).toBe('abstained')
    expect(
      resolveAgentInvestigationViewState({ requestState: 'idle', runStatus: 'FAILED' }),
    ).toBe('failed')
  })
})

describe('resolveAgentInvestigationRequestError', () => {
  it('uses safe start-copy for Candidate 404 and generic start failures', () => {
    expect(
      resolveAgentInvestigationRequestError({
        error: { statusCode: 404 },
        operation: 'start',
      }),
    ).toBe('The Candidate was not found.')
    expect(
      resolveAgentInvestigationRequestError({
        error: { statusCode: 500, data: { detail: 'private traceback' } },
        operation: 'start',
      }),
    ).toBe('The investigation could not be started.')
    expect(
      resolveAgentInvestigationRequestError({
        error: new Error('fetch failed'),
        operation: 'start',
      }),
    ).toBe('The investigation could not be started.')
  })

  it('uses safe load-copy for a missing AgentRun and generic GET failures', () => {
    expect(
      resolveAgentInvestigationRequestError({
        error: { statusCode: 404 },
        operation: 'load',
      }),
    ).toBe('The investigation was not found.')
    expect(
      resolveAgentInvestigationRequestError({
        error: { statusCode: 500, message: 'Persisted AgentRun data failed integrity validation' },
        operation: 'load',
      }),
    ).toBe('The investigation could not be loaded.')
  })
})
