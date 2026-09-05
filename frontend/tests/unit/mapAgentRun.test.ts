import { describe, expect, it } from 'vitest'
import type { CandidateEvidenceItem } from '../../app/types/candidate'
import type { AgentRunResponse } from '../../app/types/agentRunApi'
import { toAgentInvestigationPresentation } from '../../app/utils/mapAgentRun'

const CANDIDATE_ID = '20000000-0000-0000-0000-000000000001'
const AGENT_RUN_ID = '30000000-0000-0000-0000-000000000001'
const EVIDENCE_ID = '10000000-0000-0000-0000-000000000011'
const UNKNOWN_EVIDENCE_ID = '10000000-0000-0000-0000-000000000099'
const TOOL_EXECUTION_ID = '40000000-0000-0000-0000-000000000011'
const SECOND_TOOL_EXECUTION_ID = '40000000-0000-0000-0000-000000000012'

const pageEvidence: CandidateEvidenceItem[] = [
  {
    evidenceId: EVIDENCE_ID,
    sourceSystem: 'candidate-api-test',
    sourceReference: 'evidence:member-earlier',
    capturedAt: '2026-08-31T10:01:00+00:00',
    referenceUri: 'https://synthetic.invalid/member-earlier',
  },
]

function completedRun(): AgentRunResponse {
  return {
    agent_run_id: AGENT_RUN_ID,
    candidate_id: CANDIDATE_ID,
    status: 'COMPLETED',
    created_at: '2026-09-05T10:00:00+00:00',
    started_at: '2026-09-05T10:00:00+00:00',
    completed_at: '2026-09-05T10:00:01+00:00',
    stop_reason: null,
    structured_assessment: {
      outcome: 'SUPPORTED',
      conclusion: {
        statement: 'Persisted Evidence is available for human review of the Candidate hypothesis.',
        references: [{ reference_type: 'EVIDENCE', evidence_id: EVIDENCE_ID }],
      },
      supporting_claims: [
        {
          statement: 'Persisted dependency reachability context was retrieved.',
          references: [
            { reference_type: 'TOOL_EXECUTION', tool_execution_id: SECOND_TOOL_EXECUTION_ID },
          ],
        },
      ],
      missing_evidence: [],
      uncertainties: ['This deterministic investigation does not use a live model.'],
      recommendation: 'An authorized human must decide any Candidate lifecycle action.',
      stop_reason: null,
    },
    tool_executions: [
      {
        tool_execution_id: SECOND_TOOL_EXECUTION_ID,
        sequence_number: 2,
        tool_id: 'read_candidate_dependency_context',
        tool_version: '1.0.0',
        status: 'SUCCEEDED',
        duration_ms: 4,
        error_code: null,
        error_message: null,
        result_references: [],
      },
      {
        tool_execution_id: TOOL_EXECUTION_ID,
        sequence_number: 1,
        tool_id: 'read_candidate_evidence',
        tool_version: '1.0.0',
        status: 'SUCCEEDED',
        duration_ms: 8,
        error_code: null,
        error_message: null,
        result_references: [{ reference_type: 'EVIDENCE', evidence_id: EVIDENCE_ID }],
      },
    ],
    policy_decisions: [
      {
        tool_execution_id: TOOL_EXECUTION_ID,
        decision: 'ALLOW',
        requested_effect: 'READ',
        requested_risk: 'LOW',
        required_scopes: ['candidate:read'],
        rule_id: 'allow-candidate-read',
        reason_code: 'AUTHORIZED',
        decided_at: '2026-09-05T10:00:00+00:00',
      },
    ],
  }
}

describe('toAgentInvestigationPresentation', () => {
  it('maps a COMPLETED AgentRun without treating it as validation', () => {
    const presentation = toAgentInvestigationPresentation(completedRun(), pageEvidence)

    expect(presentation.status).toBe('COMPLETED')
    expect(presentation.statusLabel).toBe('Completed')
    expect(presentation.statusLabel).not.toMatch(/validat/i)
    expect(presentation.assessment?.outcome).toBe('SUPPORTED')
    expect(presentation.assessment?.outcomeLabel).toBe('Supported')
    expect(presentation.assessment?.conclusion?.statement).toContain('Persisted Evidence')
    expect(presentation.assessment?.recommendation).toContain('authorized human')
    expect(presentation.assessment?.uncertainties).toEqual([
      'This deterministic investigation does not use a live model.',
    ])
    expect(presentation).not.toHaveProperty('confidence')
    expect(presentation).not.toHaveProperty('riskScore')
    expect(presentation).not.toHaveProperty('effortScore')
  })

  it('orders tool executions by sequence_number and keeps safe fields only', () => {
    const presentation = toAgentInvestigationPresentation(completedRun(), pageEvidence)
    const toolIds = presentation.toolExecutions.map((item) => item.toolId)
    const sequences = presentation.toolExecutions.map((item) => item.sequenceNumber)

    expect(sequences).toEqual([1, 2])
    expect(toolIds).toEqual([
      'read_candidate_evidence',
      'read_candidate_dependency_context',
    ])
    expect(presentation.toolExecutions[0]?.resultReferences[0]).toMatchObject({
      referenceType: 'EVIDENCE',
      identifier: EVIDENCE_ID,
      relatedLabel: 'evidence:member-earlier',
    })
    expect(JSON.stringify(presentation.toolExecutions)).not.toContain('arguments')
    expect(JSON.stringify(presentation.toolExecutions)).not.toContain('input_hash')
    expect(JSON.stringify(presentation.toolExecutions)).not.toContain('safe_input_summary')
  })

  it('maps policy ALLOW as policy permission, not human approval', () => {
    const presentation = toAgentInvestigationPresentation(completedRun(), pageEvidence)
    const decision = presentation.policyDecisions[0]

    expect(decision?.decision).toBe('ALLOW')
    expect(decision?.decisionLabel).toBe('Policy allowed tool execution')
    expect(decision?.decisionLabel).not.toMatch(/human approved/i)
    expect(decision?.decisionLabel).not.toMatch(/approved/i)
    expect(decision?.requestedEffect).toBe('READ')
    expect(decision?.requestedRisk).toBe('LOW')
    expect(decision?.requiredScopes).toEqual(['candidate:read'])
  })

  it('reuses Candidate Evidence source references when the ID is already on the page', () => {
    const presentation = toAgentInvestigationPresentation(completedRun(), pageEvidence)
    const evidenceReference = presentation.assessment?.conclusion?.references[0]
    const toolReference = presentation.assessment?.supportingClaims[0]?.references[0]

    expect(evidenceReference).toMatchObject({
      referenceType: 'EVIDENCE',
      referenceTypeLabel: 'Evidence',
      identifier: EVIDENCE_ID,
      relatedLabel: 'evidence:member-earlier',
    })
    expect(toolReference).toMatchObject({
      referenceType: 'TOOL_EXECUTION',
      referenceTypeLabel: 'Tool execution',
      identifier: SECOND_TOOL_EXECUTION_ID,
      relatedLabel: 'read_candidate_dependency_context · sequence 2',
    })
  })

  it('does not fabricate a description when an Evidence ID is not on the page', () => {
    const run = completedRun()
    run.structured_assessment = {
      outcome: 'SUPPORTED',
      conclusion: {
        statement: 'Unknown evidence was referenced.',
        references: [{ reference_type: 'EVIDENCE', evidence_id: UNKNOWN_EVIDENCE_ID }],
      },
      supporting_claims: [],
      missing_evidence: [],
      uncertainties: [],
      recommendation: null,
      stop_reason: null,
    }

    const presentation = toAgentInvestigationPresentation(run, pageEvidence)
    expect(presentation.assessment?.conclusion?.references[0]).toMatchObject({
      identifier: UNKNOWN_EVIDENCE_ID,
      relatedLabel: null,
    })
  })

  it('maps ABSTAINED as abstention, not Candidate rejection', () => {
    const run: AgentRunResponse = {
      ...completedRun(),
      status: 'ABSTAINED',
      stop_reason: 'MISSING_EVIDENCE',
      structured_assessment: {
        outcome: 'ABSTAINED',
        conclusion: null,
        supporting_claims: [],
        missing_evidence: ['Additional corroborating evidence is needed.'],
        uncertainties: ['No live model inference was performed.'],
        recommendation: null,
        stop_reason: 'MISSING_EVIDENCE',
      },
      tool_executions: [],
      policy_decisions: [],
    }

    const presentation = toAgentInvestigationPresentation(run)

    expect(presentation.status).toBe('ABSTAINED')
    expect(presentation.statusLabel).toBe('Abstained')
    expect(presentation.statusLabel).not.toMatch(/reject/i)
    expect(presentation.stopReasonLabel).toBe('Missing evidence')
    expect(presentation.assessment?.outcomeLabel).toBe('Abstained')
    expect(presentation.assessment?.conclusion).toBeNull()
    expect(presentation.assessment?.missingEvidence).toEqual([
      'Additional corroborating evidence is needed.',
    ])
  })

  it('maps FAILED with safe status fields and no assessment', () => {
    const run: AgentRunResponse = {
      ...completedRun(),
      status: 'FAILED',
      stop_reason: 'PROVIDER_FAILURE',
      structured_assessment: null,
      tool_executions: [
        {
          tool_execution_id: TOOL_EXECUTION_ID,
          sequence_number: 1,
          tool_id: 'read_candidate_evidence',
          tool_version: '1.0.0',
          status: 'SUCCEEDED',
          duration_ms: 3,
          error_code: null,
          error_message: null,
          result_references: [],
        },
      ],
      policy_decisions: [],
    }

    const presentation = toAgentInvestigationPresentation(run)

    expect(presentation.status).toBe('FAILED')
    expect(presentation.statusLabel).toBe('Failed')
    expect(presentation.statusLabel).not.toMatch(/invalid candidate/i)
    expect(presentation.stopReason).toBe('PROVIDER_FAILURE')
    expect(presentation.stopReasonLabel).toBe('Provider failure')
    expect(presentation.assessment).toBeNull()
    expect(JSON.stringify(presentation)).not.toContain('traceback')
    expect(JSON.stringify(presentation)).not.toContain('RuntimeError')
  })

  it('maps policy DENY as a policy denial, not a human rejection', () => {
    const run = completedRun()
    run.policy_decisions = [
      {
        tool_execution_id: TOOL_EXECUTION_ID,
        decision: 'DENY',
        requested_effect: 'READ',
        requested_risk: 'LOW',
        required_scopes: ['candidate:read'],
        rule_id: 'deny-unregistered-tool',
        reason_code: 'TOOL_NOT_REGISTERED',
        decided_at: '2026-09-05T10:00:00+00:00',
      },
    ]

    const presentation = toAgentInvestigationPresentation(run)
    expect(presentation.policyDecisions[0]?.decisionLabel).toBe(
      'Policy denied tool execution',
    )
    expect(presentation.policyDecisions[0]?.decisionLabel).not.toMatch(/human rejected/i)
    expect(presentation.policyDecisions[0]?.decisionLabel).not.toMatch(/rejected/i)
  })
})
