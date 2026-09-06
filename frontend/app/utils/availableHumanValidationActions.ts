import type {
  CandidateGovernanceState,
  HumanDecisionType,
} from '../types/humanValidationApi'

const OPEN_GOVERNANCE_ACTIONS: readonly HumanDecisionType[] = [
  'VALIDATE',
  'REJECT',
  'REQUEST_INFO',
]

export function availableHumanValidationActions(
  state: CandidateGovernanceState,
): readonly HumanDecisionType[] {
  if (state === 'PENDING' || state === 'INFORMATION_REQUESTED') {
    return OPEN_GOVERNANCE_ACTIONS
  }

  return []
}
