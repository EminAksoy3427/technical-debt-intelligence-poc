import type {
  HumanValidationRequest,
  HumanValidationResponse,
} from '../types/humanValidationApi'
import { httpStatusFromUnknownError } from './resolveCandidateDetailViewState'

export type HumanValidationSubmitStatus =
  | 'success'
  | 'success-refresh-failed'
  | 'conflict'
  | 'conflict-refresh-failed'
  | 'unavailable'
  | 'not-found'
  | 'invalid'
  | 'error'

export function classifyHumanValidationError(error: unknown): Exclude<
  HumanValidationSubmitStatus,
  'success' | 'success-refresh-failed' | 'conflict-refresh-failed'
> {
  const status = httpStatusFromUnknownError(error)
  if (status === 409) {
    return 'conflict'
  }
  if (status === 403) {
    return 'unavailable'
  }
  if (status === 404) {
    return 'not-found'
  }
  if (status === 422) {
    return 'invalid'
  }
  return 'error'
}

export function humanValidationSubmitMessage(status: HumanValidationSubmitStatus): string {
  switch (status) {
    case 'success':
      return ''
    case 'success-refresh-failed':
      return 'Human Validation was saved, but the latest governance state could not be refreshed.'
    case 'conflict':
      return 'This Candidate changed since you started reviewing. The latest state has been refreshed. Review it before recording a decision.'
    case 'conflict-refresh-failed':
      return 'This Candidate changed since you started reviewing, but the latest state could not be refreshed.'
    case 'unavailable':
      return 'Human Validation is not available.'
    case 'not-found':
      return 'The Candidate was not found.'
    case 'invalid':
      return 'The Human Validation request could not be accepted.'
    case 'error':
      return 'The Human Validation decision could not be submitted.'
  }
}

export async function submitHumanValidationDecision(input: {
  candidateId: string
  payload: HumanValidationRequest
  createHumanDecision: (
    candidateId: string,
    payload: HumanValidationRequest,
  ) => Promise<HumanValidationResponse>
  refreshCandidate: () => Promise<unknown>
}): Promise<HumanValidationSubmitStatus> {
  try {
    await input.createHumanDecision(input.candidateId, input.payload)
  } catch (error) {
    const status = classifyHumanValidationError(error)
    if (status !== 'conflict') {
      return status
    }

    try {
      await input.refreshCandidate()
      return 'conflict'
    } catch {
      return 'conflict-refresh-failed'
    }
  }

  try {
    await input.refreshCandidate()
    return 'success'
  } catch {
    return 'success-refresh-failed'
  }
}
