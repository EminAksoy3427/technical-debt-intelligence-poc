import type {
  ActionApprovalPresentation,
  ActionExecutionPresentation,
  ActionPolicyDecisionPresentation,
  ActionProposalPresentation,
  ActionVerificationPresentation,
  TechnicalDebtCreationDecisionPresentation,
  TechnicalDebtDetailPresentation,
  TechnicalDebtListItem,
  TechnicalDebtSourceCandidatePresentation,
} from '../types/technicalDebt'
import type {
  ActionApproval,
  ActionExecution,
  ActionPolicyDecision,
  ActionProposal,
  ActionVerification,
  TechnicalDebtCreationDecision,
  TechnicalDebtDetail,
  TechnicalDebtSourceCandidate,
  TechnicalDebtSummary,
} from '../types/technicalDebtApi'

export function toTechnicalDebtListItem(summary: TechnicalDebtSummary): TechnicalDebtListItem {
  return {
    technicalDebtId: summary.technical_debt_id,
    lifecycleStatus: summary.lifecycle_status,
    createdAt: summary.created_at,
    sourceCandidateId: summary.source_candidate_id,
    hypothesis: summary.hypothesis,
    canonicalAssetKey: summary.canonical_asset.asset_key,
    canonicalAssetType: summary.canonical_asset.asset_type,
  }
}

export function toTechnicalDebtDetailPresentation(
  detail: TechnicalDebtDetail,
): TechnicalDebtDetailPresentation {
  return {
    technicalDebtId: detail.technical_debt_id,
    lifecycleStatus: detail.lifecycle_status,
    createdAt: detail.created_at,
    sourceCandidate: toSourceCandidatePresentation(detail.source_candidate),
    creationHumanDecision: toCreationDecisionPresentation(detail.creation_human_decision),
    actionProposals: detail.action_proposals.map(toActionProposalPresentation),
    actionApprovals: detail.action_approvals.map(toActionApprovalPresentation),
    actionPolicyDecisions: detail.action_policy_decisions.map(
      toActionPolicyDecisionPresentation,
    ),
    actionExecutions: detail.action_executions.map(toActionExecutionPresentation),
    actionVerifications: detail.action_verifications.map(toActionVerificationPresentation),
  }
}

export function toActionApprovalPresentation(
  approval: ActionApproval,
): ActionApprovalPresentation {
  return {
    actionApprovalId: approval.action_approval_id,
    actionProposalId: approval.action_proposal_id,
    payloadFingerprint: approval.payload_fingerprint,
    actorReference: approval.actor_reference,
    createdAt: approval.created_at,
  }
}

export function toActionPolicyDecisionPresentation(
  decision: ActionPolicyDecision,
): ActionPolicyDecisionPresentation {
  return {
    actionPolicyDecisionId: decision.action_policy_decision_id,
    actionProposalId: decision.action_proposal_id,
    actionApprovalId: decision.action_approval_id,
    decision: decision.decision,
    ruleId: decision.rule_id,
    reasonCode: decision.reason_code,
    createdAt: decision.created_at,
  }
}

export function toActionExecutionPresentation(
  execution: ActionExecution,
): ActionExecutionPresentation {
  return {
    actionExecutionId: execution.action_execution_id,
    actionProposalId: execution.action_proposal_id,
    technicalDebtId: execution.technical_debt_id,
    actionType: execution.action_type,
    creationPolicyDecisionId: execution.creation_policy_decision_id,
    status: execution.status,
    externalIssueId: execution.external_issue_id,
    externalIssueNumber: execution.external_issue_number,
    externalIssueUrl: execution.external_issue_url,
    safeErrorCategory: execution.safe_error_category,
    startedAt: execution.started_at,
    completedAt: execution.completed_at,
  }
}

export function toActionVerificationPresentation(
  verification: ActionVerification,
): ActionVerificationPresentation {
  return {
    actionVerificationId: verification.action_verification_id,
    actionExecutionId: verification.action_execution_id,
    result: verification.result,
    observedIssueNumber: verification.observed_issue_number,
    observedIssueUrl: verification.observed_issue_url,
    safeReasonCode: verification.safe_reason_code,
    createdAt: verification.created_at,
  }
}

export function toActionProposalPresentation(proposal: ActionProposal): ActionProposalPresentation {
  return {
    actionProposalId: proposal.action_proposal_id,
    technicalDebtId: proposal.technical_debt_id,
    actionType: proposal.action_type,
    targetRepositoryOwner: proposal.target_repository_owner,
    targetRepositoryName: proposal.target_repository_name,
    title: proposal.title,
    body: proposal.body,
    payloadFingerprint: proposal.payload_fingerprint,
    reconciliationMarker: proposal.reconciliation_marker,
    preparedBy: proposal.prepared_by,
    createdAt: proposal.created_at,
  }
}

function toSourceCandidatePresentation(
  candidate: TechnicalDebtSourceCandidate,
): TechnicalDebtSourceCandidatePresentation {
  return {
    candidateId: candidate.candidate_id,
    hypothesis: candidate.hypothesis,
    correlationRationale: candidate.correlation_rationale,
    canonicalAssetKey: candidate.canonical_asset.asset_key,
    canonicalAssetType: candidate.canonical_asset.asset_type,
  }
}

function toCreationDecisionPresentation(
  decision: TechnicalDebtCreationDecision,
): TechnicalDebtCreationDecisionPresentation {
  return {
    humanDecisionId: decision.human_decision_id,
    decision: decision.decision,
    sequenceNumber: decision.sequence_number,
    rationale: decision.rationale,
    actorReference: decision.actor_reference,
    createdAt: decision.created_at,
  }
}
