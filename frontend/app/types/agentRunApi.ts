/**
 * FastAPI AgentRun API wire DTOs.
 * These types describe JSON from POST/GET
 * /api/v1/candidates/{candidate_id}/agent-runs[/{agent_run_id}].
 * They are not validation, authorization, or TechnicalDebt.
 */

export type AgentRunStatus =
  | 'CREATED'
  | 'RUNNING'
  | 'COMPLETED'
  | 'ABSTAINED'
  | 'FAILED'

export type AgentRunStopReason =
  | 'MISSING_EVIDENCE'
  | 'CONFLICTING_EVIDENCE'
  | 'POLICY_DENIED'
  | 'BUDGET_EXHAUSTED'
  | 'TOOL_TIMEOUT'
  | 'TOOL_UNAVAILABLE'
  | 'INVALID_TOOL_ARGUMENTS'
  | 'PROVIDER_FAILURE'
  | 'INTERNAL_FAILURE'

export type AssessmentOutcome = 'SUPPORTED' | 'ABSTAINED'

export type ToolExecutionStatus =
  | 'SUCCEEDED'
  | 'DENIED'
  | 'INVALID_ARGUMENTS'
  | 'TIMED_OUT'
  | 'FAILED'
  | 'UNAVAILABLE'

export type PolicyDecision = 'ALLOW' | 'DENY'

export type ToolEffect = 'READ' | 'WRITE'

export type ToolRisk = 'LOW' | 'ELEVATED'

export interface EvidenceReferenceResponse {
  reference_type: 'EVIDENCE'
  evidence_id: string
}

export interface ToolExecutionReferenceResponse {
  reference_type: 'TOOL_EXECUTION'
  tool_execution_id: string
}

export type AssessmentReferenceResponse =
  | EvidenceReferenceResponse
  | ToolExecutionReferenceResponse

export interface GroundedClaimResponse {
  statement: string
  references: AssessmentReferenceResponse[]
}

export interface StructuredAssessmentResponse {
  outcome: AssessmentOutcome
  conclusion: GroundedClaimResponse | null
  supporting_claims: GroundedClaimResponse[]
  missing_evidence: string[]
  uncertainties: string[]
  recommendation: string | null
  stop_reason: AgentRunStopReason | null
}

export interface ToolExecutionResponse {
  tool_execution_id: string
  sequence_number: number
  tool_id: string
  tool_version: string
  status: ToolExecutionStatus
  duration_ms: number
  error_code: string | null
  error_message: string | null
  result_references: EvidenceReferenceResponse[]
}

export interface PolicyDecisionResponse {
  tool_execution_id: string
  decision: PolicyDecision
  requested_effect: ToolEffect
  requested_risk: ToolRisk
  required_scopes: string[]
  rule_id: string
  reason_code: string
  decided_at: string
}

export interface AgentRunResponse {
  agent_run_id: string
  candidate_id: string
  status: AgentRunStatus
  created_at: string
  started_at: string | null
  completed_at: string | null
  stop_reason: AgentRunStopReason | null
  structured_assessment: StructuredAssessmentResponse | null
  tool_executions: ToolExecutionResponse[]
  policy_decisions: PolicyDecisionResponse[]
}
