import type { AssetType } from './candidateApi'
import type { HumanDecisionType, TechnicalDebtLifecycleStatus } from './humanValidationApi'
import type {
  ActionExecutionErrorCategory,
  ActionExecutionStatus,
  ActionPolicyOutcome,
  ActionPolicyReasonCode,
  ActionProposalActionType,
  ActionVerificationReasonCode,
  ActionVerificationResult,
} from './technicalDebtApi'

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

export interface ActionProposalPresentation {
  actionProposalId: string
  technicalDebtId: string
  actionType: ActionProposalActionType
  targetRepositoryOwner: string
  targetRepositoryName: string
  title: string
  body: string
  payloadFingerprint: string
  reconciliationMarker: string
  preparedBy: string
  createdAt: string
}

export interface ActionApprovalPresentation {
  actionApprovalId: string
  actionProposalId: string
  payloadFingerprint: string
  actorReference: string
  createdAt: string
}

export interface ActionPolicyDecisionPresentation {
  actionPolicyDecisionId: string
  actionProposalId: string
  actionApprovalId: string | null
  decision: ActionPolicyOutcome
  ruleId: string
  reasonCode: ActionPolicyReasonCode
  createdAt: string
}

export interface ActionExecutionPresentation {
  actionExecutionId: string
  actionProposalId: string
  technicalDebtId: string
  actionType: ActionProposalActionType
  creationPolicyDecisionId: string
  status: ActionExecutionStatus
  externalIssueId: number | null
  externalIssueNumber: number | null
  externalIssueUrl: string | null
  safeErrorCategory: ActionExecutionErrorCategory | null
  startedAt: string
  completedAt: string | null
}

export interface ActionVerificationPresentation {
  actionVerificationId: string
  actionExecutionId: string
  result: ActionVerificationResult
  observedIssueNumber: number | null
  observedIssueUrl: string | null
  safeReasonCode: ActionVerificationReasonCode | null
  createdAt: string
}

export interface TechnicalDebtDetailPresentation {
  technicalDebtId: string
  lifecycleStatus: TechnicalDebtLifecycleStatus
  createdAt: string
  sourceCandidate: TechnicalDebtSourceCandidatePresentation
  creationHumanDecision: TechnicalDebtCreationDecisionPresentation
  actionProposals: ActionProposalPresentation[]
  actionApprovals: ActionApprovalPresentation[]
  actionPolicyDecisions: ActionPolicyDecisionPresentation[]
  actionExecutions: ActionExecutionPresentation[]
  actionVerifications: ActionVerificationPresentation[]
}

export const technicalDebtLifecycleStatusLabels: Record<TechnicalDebtLifecycleStatus, string> =
  {
    REGISTERED: 'Registered',
  }
