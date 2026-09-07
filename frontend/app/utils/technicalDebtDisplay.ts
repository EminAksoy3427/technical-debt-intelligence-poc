import { humanDecisionTypeLabels } from '../types/candidate'
import type { HumanDecisionType, TechnicalDebtLifecycleStatus } from '../types/humanValidationApi'
import { technicalDebtLifecycleStatusLabels } from '../types/technicalDebt'

const UNRECORDED = 'Not recorded'
const UNTITLED_TECHNICAL_DEBT = 'TechnicalDebt record'

export function technicalDebtPresentationTitle(hypothesis: string): string {
  const trimmed = hypothesis.trim()
  return trimmed.length > 0 ? trimmed : UNTITLED_TECHNICAL_DEBT
}

export function hasRecordedValue(value: string | null | undefined): boolean {
  return value != null && value.trim().length > 0
}

export function displayRecordedValue(value: string | null | undefined): string {
  if (!hasRecordedValue(value) || value == null) {
    return UNRECORDED
  }

  return value.trim()
}

export function technicalDebtLifecycleStatusDisplayLabel(status: string): string {
  if (Object.prototype.hasOwnProperty.call(technicalDebtLifecycleStatusLabels, status)) {
    return technicalDebtLifecycleStatusLabels[status as TechnicalDebtLifecycleStatus]
  }

  return status
}

export function humanDecisionTypeDisplayLabel(decision: string): string {
  if (Object.prototype.hasOwnProperty.call(humanDecisionTypeLabels, decision)) {
    return humanDecisionTypeLabels[decision as HumanDecisionType]
  }

  return decision
}

export function technicalDebtInventoryCountLabel(count: number): string {
  const noun = count === 1 ? 'TechnicalDebt record' : 'TechnicalDebt records'
  return `${count} ${noun}`
}

export function actionProposalTargetRepository(
  owner: string,
  name: string,
): string {
  return `${owner}/${name}`
}

export function newestActionProposal<T>(proposals: readonly T[]): T | null {
  if (proposals.length === 0) {
    return null
  }

  return proposals[proposals.length - 1] ?? null
}

export function previousActionProposals<T>(proposals: readonly T[]): T[] {
  if (proposals.length <= 1) {
    return []
  }

  return proposals.slice(0, -1)
}
