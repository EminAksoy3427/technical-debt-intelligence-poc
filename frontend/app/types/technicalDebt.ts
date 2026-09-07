import type { AssetType } from './candidateApi'
import type { HumanDecisionType, TechnicalDebtLifecycleStatus } from './humanValidationApi'

/**
 * Inventory presentation for one persisted TechnicalDebt.
 * This is not risk, effort, ownership, or remediation status.
 */
export interface TechnicalDebtListItem {
  technicalDebtId: string
  lifecycleStatus: TechnicalDebtLifecycleStatus
  createdAt: string
  sourceCandidateId: string
  hypothesis: string
  canonicalAssetKey: string
  canonicalAssetType: AssetType
}

export interface TechnicalDebtSourceCandidatePresentation {
  candidateId: string
  hypothesis: string
  correlationRationale: string
  canonicalAssetKey: string
  canonicalAssetType: AssetType
}

export interface TechnicalDebtCreationDecisionPresentation {
  humanDecisionId: string
  decision: HumanDecisionType
  sequenceNumber: number
  rationale: string | null
  actorReference: string
  createdAt: string
}

export interface TechnicalDebtDetailPresentation {
  technicalDebtId: string
  lifecycleStatus: TechnicalDebtLifecycleStatus
  createdAt: string
  sourceCandidate: TechnicalDebtSourceCandidatePresentation
  creationHumanDecision: TechnicalDebtCreationDecisionPresentation
}

export const technicalDebtLifecycleStatusLabels: Record<TechnicalDebtLifecycleStatus, string> =
  {
    REGISTERED: 'Registered',
  }
