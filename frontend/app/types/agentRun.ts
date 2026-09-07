import type {
  AgentRunStatus,
  AgentRunStopReason,
  AssessmentOutcome,
  PolicyDecision,
  ToolEffect,
  ToolExecutionStatus,
  ToolRisk,
} from './agentRunApi'

/**
 * Frontend presentation model for a Candidate Agent Investigation.
 * Mapped from AgentRunResponse. This is not Candidate validation,
 * human approval, authorization, or TechnicalDebt.
 */
export interface GroundingReferenceItem {
  key: string
  referenceType: 'EVIDENCE' | 'TOOL_EXECUTION'
  referenceTypeLabel: string
  identifier: string
  relatedLabel: string | null
  displayLabel: string | null
  provenanceRows: { label: string; value: string }[]
  provenanceSummaryLabel: string
}

export interface GroundedClaimItem {
  statement: string
  references: GroundingReferenceItem[]
}

export interface StructuredAssessmentPresentation {
  outcome: AssessmentOutcome
  outcomeLabel: string
  conclusion: GroundedClaimItem | null
  supportingClaims: GroundedClaimItem[]
  missingEvidence: string[]
  uncertainties: string[]
  recommendation: string | null
  stopReason: AgentRunStopReason | null
  stopReasonLabel: string | null
}

export interface ToolExecutionItem {
  toolExecutionId: string
  sequenceNumber: number
  toolId: string
  toolVersion: string
  toolDisplayLabel: string
  status: ToolExecutionStatus
  statusLabel: string
  durationMs: number
  errorCode: string | null
  errorMessage: string | null
  resultReferences: GroundingReferenceItem[]
}

export interface PolicyDecisionItem {
  toolExecutionId: string
  decision: PolicyDecision
  decisionLabel: string
  decisionStatusLabel: string
  requestedEffect: ToolEffect
  requestedEffectLabel: string
  requestedRisk: ToolRisk
  requestedRiskLabel: string
  requiredScopes: string[]
  ruleId: string
  reasonCode: string
  decidedAt: string
  toolId: string | null
  toolDisplayLabel: string | null
}

export interface AgentInvestigationPresentation {
  agentRunId: string
  candidateId: string
  status: AgentRunStatus
  statusLabel: string
  createdAt: string
  startedAt: string | null
  completedAt: string | null
  stopReason: AgentRunStopReason | null
  stopReasonLabel: string | null
  assessment: StructuredAssessmentPresentation | null
  toolExecutions: ToolExecutionItem[]
  policyDecisions: PolicyDecisionItem[]
}

export const agentRunStatusLabels: Record<AgentRunStatus, string> = {
  CREATED: 'Created',
  RUNNING: 'Running',
  COMPLETED: 'Completed',
  ABSTAINED: 'Abstained',
  FAILED: 'Failed',
}

export const agentRunStopReasonLabels: Record<AgentRunStopReason, string> = {
  MISSING_EVIDENCE: 'Missing evidence',
  CONFLICTING_EVIDENCE: 'Conflicting evidence',
  POLICY_DENIED: 'Policy denied',
  BUDGET_EXHAUSTED: 'Budget exhausted',
  TOOL_TIMEOUT: 'Tool timeout',
  TOOL_UNAVAILABLE: 'Tool unavailable',
  INVALID_TOOL_ARGUMENTS: 'Invalid tool arguments',
  PROVIDER_FAILURE: 'Provider failure',
  INTERNAL_FAILURE: 'Internal failure',
}

export const assessmentOutcomeLabels: Record<AssessmentOutcome, string> = {
  SUPPORTED: 'Supported',
  ABSTAINED: 'Abstained',
}

export const toolExecutionStatusLabels: Record<ToolExecutionStatus, string> = {
  SUCCEEDED: 'Succeeded',
  DENIED: 'Denied',
  INVALID_ARGUMENTS: 'Invalid arguments',
  TIMED_OUT: 'Timed out',
  FAILED: 'Failed',
  UNAVAILABLE: 'Unavailable',
}

export const policyDecisionLabels: Record<PolicyDecision, string> = {
  ALLOW: 'Policy allowed tool execution',
  DENY: 'Policy denied tool execution',
}

export const policyDecisionStatusLabels: Record<PolicyDecision, string> = {
  ALLOW: 'Allowed',
  DENY: 'Denied',
}
