import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const testsDirectory = dirname(fileURLToPath(import.meta.url))
const frontendAppDirectory = join(testsDirectory, '../../app')

function readFrontendSource(relativePath: string): string {
  return readFileSync(join(frontendAppDirectory, relativePath), 'utf8')
}

const detailPage = readFrontendSource('pages/candidates/[id].vue')
const investigation = readFrontendSource(
  'components/candidate/CandidateAgentInvestigation.vue',
)
const assessment = readFrontendSource(
  'components/candidate/CandidateStructuredAssessment.vue',
)
const grounding = readFrontendSource(
  'components/candidate/CandidateGroundingReferences.vue',
)
const toolTrace = readFrontendSource('components/candidate/CandidateAgentToolTrace.vue')
const policyTrace = readFrontendSource(
  'components/candidate/CandidateAgentPolicyTrace.vue',
)
const apiClient = readFrontendSource('composables/useAgentRunApi.ts')

const investigationSources = [
  detailPage,
  investigation,
  assessment,
  grounding,
  toolTrace,
  policyTrace,
].join('\n')

describe('Candidate Agent Investigation section', () => {
  it('is a Candidate Detail section after Evidence & Context', () => {
    expect(detailPage).toContain('CandidateAgentInvestigation')
    expect(detailPage).toContain("id: 'candidate-agent-investigation'")
    expect(detailPage).toContain("label: 'Agent Investigation'")
    expect(detailPage).toContain(':candidateId="presentation.candidate.candidateId"')
    expect(detailPage).toContain(':evidence="presentation.evidence"')

    const evidenceStart = detailPage.indexOf('id="candidate-evidence-context"')
    const investigationStart = detailPage.indexOf('CandidateAgentInvestigation')
    expect(evidenceStart).toBeGreaterThan(-1)
    expect(investigationStart).toBeGreaterThan(evidenceStart)
  })

  it('starts an investigation through POST with no prompt or control configuration', () => {
    expect(investigation).toContain('useAgentRunApi()')
    expect(investigation).toContain('startCandidateInvestigation')
    expect(investigation).toContain('Start Investigation')
    expect(investigation).toContain(':disabled="isStarting"')
    expect(investigation).toContain("requestState.value === 'starting'")
    expect(investigation).toContain("viewState === 'starting'")
    expect(investigation).toContain('Starting investigation.')
    expect(investigation).toContain('role="status"')
    expect(apiClient).toContain("method: 'POST'")
    expect(apiClient).not.toContain('body:')
    expect(apiClient).not.toContain('prompt')
    expect(apiClient).not.toContain('provider')
    expect(investigation).not.toContain('$fetch(')
  })

  it('renders idle, starting, and safe request-error states', () => {
    expect(investigation).toContain("requestState = ref<AgentInvestigationRequestState>('idle')")
    expect(investigation).toContain("viewState === 'starting'")
    expect(investigation).toContain("viewState === 'request-error'")
    expect(investigation).toContain('role="alert"')
    expect(investigation).toContain('resolveAgentInvestigationRequestError')
    expect(investigation).not.toContain('error.data')
    expect(investigation).not.toContain('error.message')
  })

  it('renders COMPLETED as investigation completion, not validation', () => {
    expect(investigation).toContain("presentation.status === 'COMPLETED'")
    expect(investigation).toContain('The investigation completed. This is not Candidate validation.')
    expect(investigation).toContain('CandidateStructuredAssessment')
    expect(assessment).toContain('Structured assessment')
    expect(assessment).toContain('assessment.outcomeLabel')
    expect(assessment).toContain('assessment.conclusion.statement')
    expect(assessment).toContain('assessment.supportingClaims')
    expect(assessment).toContain('assessment.missingEvidence')
    expect(assessment).toContain('assessment.uncertainties')
    expect(assessment).toContain('assessment.recommendation')
    expect(assessment).toContain('Proposed next direction')
    expect(investigationSources).not.toMatch(/Candidate validated/i)
    expect(investigationSources).not.toMatch(/Investigation validated/i)
  })

  it('renders ABSTAINED as abstention, not rejection', () => {
    expect(investigation).toContain("presentation.status === 'ABSTAINED'")
    expect(investigation).toContain(
      'The investigation stopped without a supported conclusion. This is not',
    )
    expect(investigation).toContain('Candidate rejection.')
    expect(assessment).toContain('assessment.missingEvidence')
    expect(assessment).toContain('assessment.uncertainties')
    expect(investigationSources).not.toMatch(/Candidate rejected/i)
    expect(investigationSources).not.toMatch(/\bRejected\b/)
  })

  it('renders FAILED safely and allows another Start Investigation', () => {
    expect(investigation).toContain("presentation.status === 'FAILED'")
    expect(investigation).toContain(
      'The investigation failed. This does not mean the Candidate is invalid.',
    )
    expect(investigation).toContain('presentation.stopReasonLabel')
    expect(investigation).toContain('Start Investigation')
    expect(investigation).not.toContain('retryAgentRun')
    expect(investigationSources).not.toContain('traceback')
    expect(investigationSources).not.toContain('v-html')
  })

  it('renders grounding references, tool trace, and policy trace from API fields', () => {
    expect(assessment).toContain('CandidateGroundingReferences')
    expect(grounding).toContain('Grounding references')
    expect(grounding).toContain('reference.referenceTypeLabel')
    expect(grounding).toContain('reference.identifier')
    expect(toolTrace).toContain('Tool trace')
    expect(toolTrace).toContain('execution.sequenceNumber')
    expect(toolTrace).toContain('execution.toolId')
    expect(toolTrace).toContain('execution.toolVersion')
    expect(toolTrace).toContain('execution.statusLabel')
    expect(toolTrace).toContain('execution.durationMs')
    expect(toolTrace).toContain('execution.errorCode')
    expect(toolTrace).toContain('execution.resultReferences')
    expect(policyTrace).toContain('Policy trace')
    expect(policyTrace).toContain('decision.decisionLabel')
    expect(policyTrace).toContain('decision.requestedEffect')
    expect(policyTrace).toContain('decision.requestedRisk')
    expect(policyTrace).toContain('decision.requiredScopes')
    expect(policyTrace).toContain('decision.ruleId')
    expect(policyTrace).toContain('decision.reasonCode')
    expect(policyTrace).toContain('decision.decidedAt')
  })

  it('does not represent policy ALLOW as human approval', () => {
    expect(policyTrace).toContain('Policy ALLOW is not human approval.')
    expect(investigationSources).not.toMatch(/Human Approved/i)
    expect(investigationSources).not.toMatch(/Human Rejected/i)
    expect(investigationSources).not.toMatch(/>Approved</)
    expect(investigationSources).not.toMatch(/>Rejected</)
  })

  it('does not add chat, prompt, or live-provider controls', () => {
    expect(investigationSources).not.toContain('textarea')
    expect(investigationSources).not.toContain('type="text"')
    expect(investigationSources).not.toContain('Send message')
    expect(investigationSources).not.toContain('chat')
    expect(investigationSources).not.toContain('prompt')
    expect(investigationSources).not.toContain('streaming')
    expect(investigationSources).not.toContain('avatar')
    expect(investigationSources).not.toMatch(/AI analyzed/i)
    expect(investigationSources).not.toMatch(/\bLLM\b/)
    expect(investigationSources).not.toMatch(/\bGPT\b/)
    expect(investigationSources).not.toMatch(/AI confidence/i)
    expect(investigationSources).not.toContain('OpenAI')
    expect(investigationSources).not.toContain('provider selector')
    expect(investigationSources).not.toContain('model selector')
  })

  it('does not add Human Validation or TechnicalDebt lifecycle controls', () => {
    expect(investigationSources).not.toMatch(/>Validate</)
    expect(investigationSources).not.toMatch(/>Reject</)
    expect(investigationSources).not.toMatch(/>Approve</)
    expect(investigationSources).not.toContain('Request Info')
    expect(investigationSources).not.toContain('Accept Technical Debt')
    expect(investigationSources).not.toContain('Assign Risk')
    expect(investigationSources).not.toContain('Assign Effort')
    expect(investigationSources).not.toContain('chain-of-thought')
    expect(investigationSources).not.toContain('DATABASE_URL')
  })
})
