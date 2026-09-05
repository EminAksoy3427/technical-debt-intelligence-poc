import type { AgentRunStatus } from '../types/agentRunApi'
import { httpStatusFromUnknownError } from './resolveCandidateDetailViewState'

export type AgentInvestigationRequestState = 'idle' | 'starting' | 'error'

export type AgentInvestigationViewState =
  | 'idle'
  | 'starting'
  | 'request-error'
  | 'created'
  | 'running'
  | 'completed'
  | 'abstained'
  | 'failed'

export function resolveAgentInvestigationViewState(input: {
  requestState: AgentInvestigationRequestState
  runStatus: AgentRunStatus | null | undefined
}): AgentInvestigationViewState {
  if (input.requestState === 'starting') {
    return 'starting'
  }

  if (input.requestState === 'error') {
    return 'request-error'
  }

  switch (input.runStatus) {
    case 'CREATED':
      return 'created'
    case 'RUNNING':
      return 'running'
    case 'COMPLETED':
      return 'completed'
    case 'ABSTAINED':
      return 'abstained'
    case 'FAILED':
      return 'failed'
    default:
      return 'idle'
  }
}

export function resolveAgentInvestigationRequestError(input: {
  error: unknown
  operation: 'start' | 'load'
}): string {
  const status = httpStatusFromUnknownError(input.error)
  if (input.operation === 'start') {
    if (status === 404) {
      return 'The Candidate was not found.'
    }
    return 'The investigation could not be started.'
  }

  if (status === 404) {
    return 'The investigation was not found.'
  }
  return 'The investigation could not be loaded.'
}
