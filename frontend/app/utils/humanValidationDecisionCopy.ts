import {
  candidateGovernanceStateLabels,
  humanDecisionTypeLabels,
} from '../types/candidate'
import type {
  CandidateGovernanceState,
  HumanDecisionType,
} from '../types/humanValidationApi'

export const HUMAN_VALIDATION_HEADER_HELPER =
  'Review the available evidence and record a governance decision.'

export const HUMAN_VALIDATION_DISTINCTION =
  'AI investigation is decision support. This decision is recorded by a human reviewer.'

export const HUMAN_VALIDATION_VALIDATE_CONSEQUENCE =
  'Validation confirms this Candidate as TechnicalDebt and creates the corresponding governed record.'

export const HUMAN_VALIDATION_REJECT_HELPER =
  'This records that evidence does not support validation. The Candidate is not deleted.'

export const HUMAN_VALIDATION_REQUEST_INFO_HELPER =
  'This records a request for more information. The Candidate is not validated or rejected.'

export const HUMAN_VALIDATION_SUBMIT_HELPER =
  'This records a human governance decision.'

export const HUMAN_VALIDATION_SELECT_PROMPT = 'Select a decision to continue.'

export const HUMAN_VALIDATION_CLOSED_HELPER =
  'A human governance decision has already been recorded for this Candidate.'

export const humanValidationDecisionDescriptions: Record<HumanDecisionType, string> = {
  VALIDATE: 'Confirm this Candidate as TechnicalDebt.',
  REJECT: 'Evidence does not support validation.',
  REQUEST_INFO: 'More evidence or context is required.',
}

export const humanValidationSubmitLabels: Record<HumanDecisionType, string> = {
  VALIDATE: 'Validate Candidate',
  REJECT: 'Reject Candidate',
  REQUEST_INFO: 'Request information',
}

export function humanValidationDecisionLabel(decision: HumanDecisionType): string {
  return humanDecisionTypeLabels[decision]
}

export function humanValidationSubmitLabel(decision: HumanDecisionType): string {
  return humanValidationSubmitLabels[decision]
}

export function humanDecisionResultingGovernanceState(
  decision: HumanDecisionType,
): CandidateGovernanceState {
  if (decision === 'VALIDATE') {
    return 'VALIDATED'
  }

  if (decision === 'REJECT') {
    return 'REJECTED'
  }

  return 'INFORMATION_REQUESTED'
}

export function humanDecisionResultingGovernanceLabel(decision: HumanDecisionType): string {
  return candidateGovernanceStateLabels[humanDecisionResultingGovernanceState(decision)]
}

export function formatHumanValidationEvidenceCount(count: number): string {
  if (count === 0) {
    return 'None recorded'
  }

  if (count === 1) {
    return '1 item'
  }

  return `${count} items`
}
