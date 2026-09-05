import type { CandidateEvidenceItem } from '../types/candidate'
import type {
  AgentInvestigationPresentation,
  GroundedClaimItem,
  GroundingReferenceItem,
  PolicyDecisionItem,
  StructuredAssessmentPresentation,
  ToolExecutionItem,
} from '../types/agentRun'
import {
  agentRunStatusLabels,
  agentRunStopReasonLabels,
  assessmentOutcomeLabels,
  policyDecisionLabels,
  toolExecutionStatusLabels,
} from '../types/agentRun'
import type {
  AgentRunResponse,
  AgentRunStopReason,
  AssessmentReferenceResponse,
  EvidenceReferenceResponse,
  GroundedClaimResponse,
  PolicyDecisionResponse,
  StructuredAssessmentResponse,
  ToolExecutionResponse,
} from '../types/agentRunApi'

export function toAgentInvestigationPresentation(
  run: AgentRunResponse,
  evidence: readonly CandidateEvidenceItem[] = [],
): AgentInvestigationPresentation {
  const evidenceById = new Map(evidence.map((item) => [item.evidenceId, item]))
  const toolExecutions = [...run.tool_executions]
    .sort((left, right) => left.sequence_number - right.sequence_number)
    .map((execution) => toToolExecutionItem(execution, evidenceById))
  const toolExecutionsById = new Map(
    toolExecutions.map((item) => [item.toolExecutionId, item]),
  )

  return {
    agentRunId: run.agent_run_id,
    candidateId: run.candidate_id,
    status: run.status,
    statusLabel: agentRunStatusLabels[run.status],
    createdAt: run.created_at,
    startedAt: run.started_at,
    completedAt: run.completed_at,
    stopReason: run.stop_reason,
    stopReasonLabel: stopReasonLabel(run.stop_reason),
    assessment: toStructuredAssessmentPresentation(
      run.structured_assessment,
      evidenceById,
      toolExecutionsById,
    ),
    toolExecutions,
    policyDecisions: run.policy_decisions.map(toPolicyDecisionItem),
  }
}

function toStructuredAssessmentPresentation(
  assessment: StructuredAssessmentResponse | null,
  evidenceById: ReadonlyMap<string, CandidateEvidenceItem>,
  toolExecutionsById: ReadonlyMap<string, ToolExecutionItem>,
): StructuredAssessmentPresentation | null {
  if (assessment == null) {
    return null
  }

  return {
    outcome: assessment.outcome,
    outcomeLabel: assessmentOutcomeLabels[assessment.outcome],
    conclusion:
      assessment.conclusion == null
        ? null
        : toGroundedClaimItem(assessment.conclusion, evidenceById, toolExecutionsById, 'conclusion'),
    supportingClaims: assessment.supporting_claims.map((claim, index) =>
      toGroundedClaimItem(claim, evidenceById, toolExecutionsById, `supporting-${index}`),
    ),
    missingEvidence: [...assessment.missing_evidence],
    uncertainties: [...assessment.uncertainties],
    recommendation: assessment.recommendation,
    stopReason: assessment.stop_reason,
    stopReasonLabel: stopReasonLabel(assessment.stop_reason),
  }
}

function toGroundedClaimItem(
  claim: GroundedClaimResponse,
  evidenceById: ReadonlyMap<string, CandidateEvidenceItem>,
  toolExecutionsById: ReadonlyMap<string, ToolExecutionItem>,
  keyPrefix: string,
): GroundedClaimItem {
  return {
    statement: claim.statement,
    references: claim.references.map((reference, index) =>
      toGroundingReferenceItem(
        reference,
        evidenceById,
        toolExecutionsById,
        `${keyPrefix}-${index}`,
      ),
    ),
  }
}

function toToolExecutionItem(
  execution: ToolExecutionResponse,
  evidenceById: ReadonlyMap<string, CandidateEvidenceItem>,
): ToolExecutionItem {
  return {
    toolExecutionId: execution.tool_execution_id,
    sequenceNumber: execution.sequence_number,
    toolId: execution.tool_id,
    toolVersion: execution.tool_version,
    status: execution.status,
    statusLabel: toolExecutionStatusLabels[execution.status],
    durationMs: execution.duration_ms,
    errorCode: execution.error_code,
    errorMessage: execution.error_message,
    resultReferences: execution.result_references.map((reference, index) =>
      toEvidenceReferenceItem(
        reference,
        evidenceById,
        `${execution.tool_execution_id}-result-${index}`,
      ),
    ),
  }
}

function toPolicyDecisionItem(decision: PolicyDecisionResponse): PolicyDecisionItem {
  return {
    toolExecutionId: decision.tool_execution_id,
    decision: decision.decision,
    decisionLabel: policyDecisionLabels[decision.decision],
    requestedEffect: decision.requested_effect,
    requestedRisk: decision.requested_risk,
    requiredScopes: [...decision.required_scopes],
    ruleId: decision.rule_id,
    reasonCode: decision.reason_code,
    decidedAt: decision.decided_at,
  }
}

function toGroundingReferenceItem(
  reference: AssessmentReferenceResponse,
  evidenceById: ReadonlyMap<string, CandidateEvidenceItem>,
  toolExecutionsById: ReadonlyMap<string, ToolExecutionItem>,
  key: string,
): GroundingReferenceItem {
  if (reference.reference_type === 'EVIDENCE') {
    return toEvidenceReferenceItem(reference, evidenceById, key)
  }

  const execution = toolExecutionsById.get(reference.tool_execution_id)
  return {
    key,
    referenceType: 'TOOL_EXECUTION',
    referenceTypeLabel: 'Tool execution',
    identifier: reference.tool_execution_id,
    relatedLabel:
      execution == null ? null : `${execution.toolId} · sequence ${execution.sequenceNumber}`,
  }
}

function toEvidenceReferenceItem(
  reference: EvidenceReferenceResponse,
  evidenceById: ReadonlyMap<string, CandidateEvidenceItem>,
  key: string,
): GroundingReferenceItem {
  const evidence = evidenceById.get(reference.evidence_id)
  return {
    key,
    referenceType: 'EVIDENCE',
    referenceTypeLabel: 'Evidence',
    identifier: reference.evidence_id,
    relatedLabel: evidence?.sourceReference ?? null,
  }
}

function stopReasonLabel(stopReason: AgentRunStopReason | null): string | null {
  return stopReason == null ? null : agentRunStopReasonLabels[stopReason]
}
