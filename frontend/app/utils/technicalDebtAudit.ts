import type {
  ActionApprovalPresentation,
  ActionExecutionPresentation,
  ActionPolicyDecisionPresentation,
  ActionProposalPresentation,
  ActionVerificationPresentation,
} from '../types/technicalDebt'

export type TechnicalDebtAuditItemType =
  | 'TECHNICAL_DEBT_REGISTERED'
  | 'ACTION_PROPOSAL_PREPARED'
  | 'HUMAN_APPROVAL_RECORDED'
  | 'POLICY_DECISION'
  | 'ACTION_EXECUTION'
  | 'ACTION_VERIFICATION'

export interface TechnicalDebtAuditItem {
  id: string
  type: TechnicalDebtAuditItemType
  label: string
  timestamp: string
  relationship: string | null
}

const typeOrder: Record<TechnicalDebtAuditItemType, number> = {
  TECHNICAL_DEBT_REGISTERED: 0,
  ACTION_PROPOSAL_PREPARED: 1,
  HUMAN_APPROVAL_RECORDED: 2,
  POLICY_DECISION: 3,
  ACTION_EXECUTION: 4,
  ACTION_VERIFICATION: 5,
}

export function buildTechnicalDebtAuditTimeline(input: {
  technicalDebtId: string
  technicalDebtCreatedAt: string
  actionProposals: readonly ActionProposalPresentation[]
  actionApprovals: readonly ActionApprovalPresentation[]
  actionPolicyDecisions: readonly ActionPolicyDecisionPresentation[]
  actionExecutions: readonly ActionExecutionPresentation[]
  actionVerifications: readonly ActionVerificationPresentation[]
}): TechnicalDebtAuditItem[] {
  const items: TechnicalDebtAuditItem[] = [
    {
      id: input.technicalDebtId,
      type: 'TECHNICAL_DEBT_REGISTERED',
      label: 'Technical Debt Registered',
      timestamp: input.technicalDebtCreatedAt,
      relationship: null,
    },
  ]

  for (const proposal of input.actionProposals) {
    items.push({
      id: proposal.actionProposalId,
      type: 'ACTION_PROPOSAL_PREPARED',
      label: 'Action Proposal Prepared',
      timestamp: proposal.createdAt,
      relationship: `Proposal ${proposal.actionProposalId}`,
    })
  }
  for (const approval of input.actionApprovals) {
    items.push({
      id: approval.actionApprovalId,
      type: 'HUMAN_APPROVAL_RECORDED',
      label: 'Human Approval Recorded',
      timestamp: approval.createdAt,
      relationship: `Proposal ${approval.actionProposalId}`,
    })
  }
  for (const decision of input.actionPolicyDecisions) {
    items.push({
      id: decision.actionPolicyDecisionId,
      type: 'POLICY_DECISION',
      label: decision.decision === 'ALLOW' ? 'Policy Allowed' : 'Policy Denied',
      timestamp: decision.createdAt,
      relationship: `Proposal ${decision.actionProposalId}`,
    })
  }
  for (const execution of input.actionExecutions) {
    const label = {
      IN_PROGRESS: 'External Execution Started',
      SUCCEEDED: 'External Execution Succeeded',
      FAILED: 'External Execution Failed',
      UNKNOWN: 'External Execution Unknown',
    }[execution.status]
    items.push({
      id: execution.actionExecutionId,
      type: 'ACTION_EXECUTION',
      label,
      timestamp: execution.completedAt ?? execution.startedAt,
      relationship: `Proposal ${execution.actionProposalId}`,
    })
  }
  for (const verification of input.actionVerifications) {
    const label = {
      PASS: 'Verification Passed',
      FAIL: 'Verification Failed',
      UNAVAILABLE: 'Verification Unavailable',
    }[verification.result]
    items.push({
      id: verification.actionVerificationId,
      type: 'ACTION_VERIFICATION',
      label,
      timestamp: verification.createdAt,
      relationship: `Execution ${verification.actionExecutionId}`,
    })
  }

  return items.sort(
    (left, right) =>
      Date.parse(left.timestamp) - Date.parse(right.timestamp) ||
      typeOrder[left.type] - typeOrder[right.type] ||
      left.id.localeCompare(right.id),
  )
}
