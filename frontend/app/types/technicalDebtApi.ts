/**
 * FastAPI TechnicalDebt API wire DTOs.
 * These types describe JSON from GET /api/v1/technical-debts,
 * GET /api/v1/technical-debts/{technical_debt_id}, and
 * the governed action mutation endpoints below that detail resource.
 * REGISTERED is the only lifecycle status the API currently returns.
 * CREATE_GITHUB_ISSUE is the only ActionProposal action type currently returned.
 */

import type { CanonicalAssetResponse } from './candidateApi'
import type { HumanDecisionType, TechnicalDebtLifecycleStatus } from './humanValidationApi'

export interface TechnicalDebtSummary {
  technical_debt_id: string
  lifecycle_status: TechnicalDebtLifecycleStatus
  created_at: string
  source_candidate_id: string
  hypothesis: string
  canonical_asset: CanonicalAssetResponse
}

export interface TechnicalDebtListResponse {
  items: TechnicalDebtSummary[]
  count: number
}

export interface TechnicalDebtSourceCandidate {
  candidate_id: string
  hypothesis: string
  correlation_rationale: string
  canonical_asset: CanonicalAssetResponse
}

export interface TechnicalDebtCreationDecision {
  human_decision_id: string
  decision: HumanDecisionType
  sequence_number: number
  rationale: string | null
  actor_reference: string
  created_at: string
}

export type ActionProposalActionType = 'CREATE_GITHUB_ISSUE'

export interface ActionProposal {
  action_proposal_id: string
  technical_debt_id: string
  action_type: ActionProposalActionType
  target_repository_owner: string
  target_repository_name: string
  title: string
  body: string
  payload_fingerprint: string
  reconciliation_marker: string
  prepared_by: string
  created_at: string
}

export interface ApproveActionProposalRequest {
  expected_payload_fingerprint: string
}

export interface ActionApproval {
  action_approval_id: string
  action_proposal_id: string
  payload_fingerprint: string
  actor_reference: string
  created_at: string
}

export type ActionPolicyOutcome = 'ALLOW' | 'DENY'
export type ActionPolicyReasonCode =
  | 'APPROVAL_MISSING'
  | 'FINGERPRINT_MISMATCH'
  | 'ACTION_TYPE_NOT_ALLOWED'
  | 'REPOSITORY_NOT_ALLOWLISTED'
  | 'EXECUTION_DISABLED'
  | 'POLICY_ALLOWED'

export interface ActionPolicyDecision {
  action_policy_decision_id: string
  action_proposal_id: string
  action_approval_id: string | null
  decision: ActionPolicyOutcome
  rule_id: string
  reason_code: ActionPolicyReasonCode
  created_at: string
}

export type ActionExecutionStatus = 'IN_PROGRESS' | 'SUCCEEDED' | 'FAILED' | 'UNKNOWN'
export type ActionExecutionErrorCategory =
  | 'EXTERNAL_REJECTED'
  | 'NOT_SENT'
  | 'TRANSPORT_UNKNOWN'

export interface ActionExecution {
  action_execution_id: string
  action_proposal_id: string
  technical_debt_id: string
  action_type: ActionProposalActionType
  creation_policy_decision_id: string
  status: ActionExecutionStatus
  external_issue_id: number | null
  external_issue_number: number | null
  external_issue_url: string | null
  safe_error_category: ActionExecutionErrorCategory | null
  started_at: string
  completed_at: string | null
}

export type ActionVerificationResult = 'PASS' | 'FAIL' | 'UNAVAILABLE'
export type ActionVerificationReasonCode =
  | 'TITLE_MISMATCH'
  | 'FINGERPRINT_MISMATCH'
  | 'MARKER_MISSING'
  | 'PULL_REQUEST'
  | 'REFERENCE_MISMATCH'
  | 'TRANSPORT_UNAVAILABLE'

export interface ActionVerification {
  action_verification_id: string
  action_execution_id: string
  result: ActionVerificationResult
  observed_issue_number: number | null
  observed_issue_url: string | null
  safe_reason_code: ActionVerificationReasonCode | null
  created_at: string
}

export interface TechnicalDebtDetail {
  technical_debt_id: string
  lifecycle_status: TechnicalDebtLifecycleStatus
  created_at: string
  source_candidate: TechnicalDebtSourceCandidate
  creation_human_decision: TechnicalDebtCreationDecision
  action_proposals: ActionProposal[]
  action_approvals: ActionApproval[]
  action_policy_decisions: ActionPolicyDecision[]
  action_executions: ActionExecution[]
  action_verifications: ActionVerification[]
}
