/**
 * FastAPI TechnicalDebt API wire DTOs.
 * These types describe JSON from GET /api/v1/technical-debts,
 * GET /api/v1/technical-debts/{technical_debt_id}, and
 * POST /api/v1/technical-debts/{technical_debt_id}/action-proposals.
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

export interface TechnicalDebtDetail {
  technical_debt_id: string
  lifecycle_status: TechnicalDebtLifecycleStatus
  created_at: string
  source_candidate: TechnicalDebtSourceCandidate
  creation_human_decision: TechnicalDebtCreationDecision
  action_proposals: ActionProposal[]
}
