/**
 * FastAPI Human Validation wire DTOs.
 * These types describe JSON from Candidate Detail governance and
 * POST /api/v1/candidates/{candidate_id}/human-decisions.
 * They are not L4 approval and are not TechnicalDebt lifecycle beyond
 * the VALIDATE side-effect returned by the API.
 */

export type CandidateGovernanceState =
  | 'PENDING'
  | 'INFORMATION_REQUESTED'
  | 'VALIDATED'
  | 'REJECTED'

export type HumanDecisionType = 'VALIDATE' | 'REJECT' | 'REQUEST_INFO'

export type TechnicalDebtLifecycleStatus = 'REGISTERED'

export interface HumanDecision {
  human_decision_id: string
  sequence_number: number
  decision: HumanDecisionType
  rationale: string | null
  requested_information: string | null
  actor_reference: string
  created_at: string
}

export interface HumanValidationDecision extends HumanDecision {
  candidate_id: string
}

export interface CandidateGovernanceTechnicalDebt {
  technical_debt_id: string
  lifecycle_status: TechnicalDebtLifecycleStatus
  created_at: string
  source_candidate_id: string
}

export interface CandidateGovernance {
  state: CandidateGovernanceState
  revision: number
  decisions: HumanDecision[]
  technical_debt: CandidateGovernanceTechnicalDebt | null
}

export interface HumanValidationRequest {
  decision: HumanDecisionType
  rationale?: string
  requested_information?: string
  expected_governance_revision: number
}

export interface HumanValidationGovernance {
  state: CandidateGovernanceState
  revision: number
}

export interface HumanValidationResponse {
  human_decision: HumanValidationDecision
  governance: HumanValidationGovernance
  technical_debt: CandidateGovernanceTechnicalDebt | null
}
