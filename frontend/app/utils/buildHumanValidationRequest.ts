import type {
  HumanDecisionType,
  HumanValidationRequest,
} from '../types/humanValidationApi'

export function humanValidationClientValidationMessage(
  decision: HumanDecisionType,
  rationale: string,
  requestedInformation: string,
): string | null {
  if (decision === 'REQUEST_INFO') {
    return requestedInformation.trim() === '' ? 'Requested information is required.' : null
  }

  return rationale.trim() === '' ? 'Rationale is required.' : null
}

export function buildHumanValidationRequest(input: {
  decision: HumanDecisionType
  expectedGovernanceRevision: number
  rationale: string
  requestedInformation: string
}): HumanValidationRequest {
  if (input.decision === 'REQUEST_INFO') {
    return {
      decision: 'REQUEST_INFO',
      requested_information: input.requestedInformation.trim(),
      expected_governance_revision: input.expectedGovernanceRevision,
    }
  }

  return {
    decision: input.decision,
    rationale: input.rationale.trim(),
    expected_governance_revision: input.expectedGovernanceRevision,
  }
}
