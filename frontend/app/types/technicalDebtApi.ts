/**
 * FastAPI TechnicalDebt API wire DTOs.
 * These types describe JSON from GET /api/v1/technical-debts and
 * GET /api/v1/technical-debts/{technical_debt_id}.
 * REGISTERED is the only lifecycle status the API currently returns.
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

export interface TechnicalDebtDetail {
  technical_debt_id: string
  lifecycle_status: TechnicalDebtLifecycleStatus
  created_at: string
  source_candidate: TechnicalDebtSourceCandidate
  creation_human_decision: TechnicalDebtCreationDecision
}
