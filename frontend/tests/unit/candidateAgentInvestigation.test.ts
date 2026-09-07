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
const tabDefs = readFrontendSource('utils/candidateDetailTabs.ts')
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
const display = readFrontendSource('utils/candidateDetailDisplay.ts')
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
    expect(tabDefs).toContain("id: 'investigation'")
    expect(tabDefs).toContain("label: 'AI Investigation'")
    expect(tabDefs).toContain("panelId: 'candidate-agent-investigation'")
    expect(detailPage).toContain(':candidateId="presentation.candidate.candidateId"')
    expect(detailPage).toContain(':evidence="presentation.evidence"')
    expect(detailPage).toContain(':isActive="selectedTab === \'investigation\'"')

    const evidenceStart = detailPage.indexOf('id="candidate-evidence-context"')
    const investigationStart = detailPage.indexOf('CandidateAgentInvestigation')
    expect(evidenceStart).toBeGreaterThan(-1)
    expect(investigationStart).toBeGreaterThan(evidenceStart)
  })

  it('keeps hidden-tab mount behavior unchanged', () => {
    expect(investigation).toContain(':hidden="!isActive"')
    expect(investigation).toContain('role="tabpanel"')
    expect(investigation).not.toContain('v-if="isActive"')
    expect(detailPage).not.toContain('v-if="selectedTab')
    expect(detailPage).toContain(':isActive="selectedTab === \'investigation\'"')
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

  it('renders one human-readable status and keeps raw status in run details', () => {
    expect(investigation).toContain('presentation.statusLabel')
    expect(investigation).toContain('summary-label="Run details"')
    expect(investigation).toContain('statusProvenanceRows')
    expect(investigation).toContain("label: 'Status', value: presentation.value.status")
    expect(investigation).not.toContain('class="candidate-identifier">{{ presentation.status }}')
    expect(investigation).not.toContain('<h3 id="candidate-investigation-status-heading">Summary</h3>')
  })

  it('renders COMPLETED as investigation completion, not validation', () => {
    expect(investigation).toContain("presentation.status === 'COMPLETED'")
    expect(investigation).toContain('The investigation completed. This is not Candidate validation.')
    expect(investigation).toContain('CandidateStructuredAssessment')
    expect(assessment).toContain('Assessment')
    expect(assessment).toContain('assessment.outcomeLabel')
    expect(assessment).toContain('assessment.conclusion.statement')
    expect(assessment).toContain('assessment.supportingClaims')
    expect(assessment).toContain('assessment.missingEvidence')
    expect(assessment).toContain('assessment.uncertainties')
    expect(assessment).toContain('assessment.recommendation')
    expect(assessment).toContain('Recommended next steps')
    expect(assessment).toContain('Proposed next direction, not an approved action.')
    expect(investigationSources).not.toMatch(/Candidate validated/i)
    expect(investigationSources).not.toMatch(/Investigation validated/i)
  })

  it('keeps missing evidence, uncertainties, and recommendations visible', () => {
    expect(assessment).toContain('Evidence gaps')
    expect(assessment).toContain('Missing evidence')
    expect(assessment).toContain('Uncertainties')
    expect(assessment).toContain('assessment.missingEvidence')
    expect(assessment).toContain('assessment.uncertainties')
    expect(assessment).toContain('Recommended next steps')
    expect(assessment).toContain('assessment.recommendation')
    expect(assessment).toContain('None recorded.')
    expect(assessment).toContain('candidate-assessment-gaps-heading')
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

  it('renders FAILED safely and allows another investigation run', () => {
    expect(investigation).toContain("presentation.status === 'FAILED'")
    expect(investigation).toContain(
      'The investigation failed. This does not mean the Candidate is invalid.',
    )
    expect(investigation).toContain('presentation.stopReasonLabel')
    expect(investigation).toContain('Start Investigation')
    expect(investigation).toContain('Run investigation again')
    expect(investigation).toContain('startInvestigation')
    expect(investigation).not.toContain('retryAgentRun')
    expect(investigationSources).not.toContain('traceback')
    expect(investigationSources).not.toContain('v-html')
  })

  it('renders grounding references with claims first and provenance available', () => {
    expect(assessment).toContain('CandidateGroundingReferences')
    expect(assessment).toContain('Supporting findings')
    expect(grounding).toContain('Grounded by')
    expect(grounding).toContain('reference.referenceTypeLabel')
    expect(grounding).toContain('reference.displayLabel')
    expect(grounding).toContain('CandidateProvenanceDetails')
    expect(grounding).toContain('reference.provenanceRows')
    expect(grounding).not.toContain('class="candidate-identifier candidate-breakable">{{ reference.identifier }}')
  })

  it('keeps tool and policy traces accessible inside collapsed investigation details', () => {
    expect(investigation).toContain('<summary>Investigation details</summary>')
    expect(investigation).toContain(
      '<details class="candidate-disclosure candidate-investigation-details">',
    )
    expect(investigation).not.toContain(
      '<details class="candidate-disclosure candidate-investigation-details" open',
    )
    expect(toolTrace).toContain('Tool activity')
    expect(toolTrace).toContain('execution.sequenceNumber')
    expect(toolTrace).toContain('execution.toolDisplayLabel')
    expect(toolTrace).toContain('execution.toolId')
    expect(toolTrace).toContain('execution.toolVersion')
    expect(toolTrace).toContain('execution.statusLabel')
    expect(toolTrace).toContain('execution.durationMs')
    expect(toolTrace).toContain('execution.errorCode')
    expect(toolTrace).toContain('execution.resultReferences')
    expect(policyTrace).toContain('Policy decisions')
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
    expect(policyTrace).toContain('Runtime policy allowed this tool execution.')
    expect(policyTrace).toContain("decision.decision === 'ALLOW'")
    expect(investigationSources).not.toMatch(/Human Approved/i)
    expect(investigationSources).not.toMatch(/Human Rejected/i)
    expect(investigationSources).not.toMatch(/>Approved</)
    expect(investigationSources).not.toMatch(/>Rejected</)
    expect(investigationSources).not.toMatch(/Governance approved/i)
    expect(investigationSources).not.toContain('Human approved')
  })

  it('humanizes known tool names and keeps a safe unknown-tool fallback', () => {
    expect(display).toContain('read_candidate_evidence')
    expect(display).toContain('Read candidate evidence')
    expect(display).toContain('read_candidate_dependency_context')
    expect(display).toContain('Read dependency context')
    expect(display).toContain('read_candidate_enterprise_context')
    expect(display).toContain('Read enterprise context')
    expect(display).toContain('formatToolDisplayLabel')
    expect(display).toContain("toolId.split(/[-_]+/)")
    expect(toolTrace).toContain('execution.toolDisplayLabel')
    expect(toolTrace).toContain('execution.toolId')
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
    expect(investigationSources).not.toContain('Fix automatically')
    expect(investigationSources).not.toContain('Accept risk')
    expect(investigationSources).not.toMatch(/>Execute</)
  })
})
