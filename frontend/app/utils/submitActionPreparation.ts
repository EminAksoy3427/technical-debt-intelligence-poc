import type { ActionProposal } from '../types/technicalDebtApi'
import { httpStatusFromUnknownError } from './resolveCandidateDetailViewState'

export type ActionPreparationSubmitStatus =
  | 'success'
  | 'success-refresh-failed'
  | 'unavailable'
  | 'not-found'
  | 'conflict'
  | 'invalid'
  | 'error'

export function classifyActionPreparationError(
  error: unknown,
): Exclude<ActionPreparationSubmitStatus, 'success' | 'success-refresh-failed'> {
  const status = httpStatusFromUnknownError(error)
  if (status === 503) {
    return 'unavailable'
  }
  if (status === 404) {
    return 'not-found'
  }
  if (status === 409) {
    return 'conflict'
  }
  if (status === 422) {
    return 'invalid'
  }
  return 'error'
}

export function actionPreparationSubmitMessage(
  status: ActionPreparationSubmitStatus,
): string {
  switch (status) {
    case 'success':
      return ''
    case 'success-refresh-failed':
      return 'The GitHub issue preview was prepared, but TechnicalDebt details could not be refreshed.'
    case 'unavailable':
      return 'Action preparation is unavailable because the server is not configured.'
    case 'not-found':
      return 'The TechnicalDebt was not found.'
    case 'conflict':
      return 'The GitHub issue preview could not be prepared because of a conflict.'
    case 'invalid':
      return 'The action preparation request could not be accepted.'
    case 'error':
      return 'The GitHub issue preview could not be prepared.'
  }
}

export async function submitActionPreparation(input: {
  technicalDebtId: string
  prepareActionProposal: (technicalDebtId: string) => Promise<ActionProposal>
  refreshTechnicalDebt: () => Promise<unknown>
}): Promise<{
  status: ActionPreparationSubmitStatus
  proposal: ActionProposal | null
}> {
  let proposal: ActionProposal
  try {
    proposal = await input.prepareActionProposal(input.technicalDebtId)
  } catch (error) {
    return {
      status: classifyActionPreparationError(error),
      proposal: null,
    }
  }

  try {
    await input.refreshTechnicalDebt()
    return { status: 'success', proposal }
  } catch {
    return { status: 'success-refresh-failed', proposal }
  }
}
