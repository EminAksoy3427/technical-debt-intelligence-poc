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
const humanValidation = readFrontendSource(
  'components/candidate/CandidateHumanValidation.vue',
)
const investigation = readFrontendSource(
  'components/candidate/CandidateAgentInvestigation.vue',
)
const requestBuilder = readFrontendSource('utils/buildHumanValidationRequest.ts')
const apiClient = readFrontendSource('composables/useHumanValidationApi.ts')
const labels = readFrontendSource('types/candidate.ts')

const humanValidationSources = [humanValidation, requestBuilder, apiClient].join('\n')

describe('Candidate Human Validation section', () => {
  it('is a Candidate Detail section after Agent Investigation', () => {
    expect(detailPage).toContain('CandidateHumanValidation')
    expect(detailPage).toContain("id: 'candidate-human-validation'")
    expect(detailPage).toContain("label: 'Human Validation'")
    expect(detailPage).toContain(':governance="presentation.governance"')
    expect(detailPage).toContain(':refreshCandidate="refresh"')
    expect(humanValidation).toContain('id="candidate-human-validation"')
    expect(humanValidation).toContain('Human Validation')

    const investigationStart = detailPage.indexOf('CandidateAgentInvestigation')
    const validationStart = detailPage.indexOf('CandidateHumanValidation')
    expect(validationStart).toBeGreaterThan(investigationStart)
  })

  it('keeps Agent Investigation visually separate from Human Validation', () => {
    expect(investigation).toContain('id="candidate-agent-investigation"')
    expect(investigation).not.toContain('createHumanDecision')
    expect(investigation).not.toContain('Submit decision')
    expect(humanValidation).not.toContain('Start Investigation')
    expect(humanValidation).not.toContain('structured_assessment')
    expect(humanValidation).toContain('not Agent Investigation')
  })

  it('shows persisted PENDING governance, revision, and decision actions', () => {
    expect(humanValidation).toContain('candidateGovernanceStateLabels[governance.state]')
    expect(humanValidation).toContain('governance.revision')
    expect(humanValidation).toContain('availableHumanValidationActions')
    expect(humanValidation).toContain('humanDecisionTypeLabels[action]')
    expect(labels).toContain("VALIDATE: 'Validate'")
    expect(labels).toContain("REJECT: 'Reject'")
    expect(labels).toContain("REQUEST_INFO: 'Request information'")
    expect(humanValidation).not.toContain('Approve')
    expect(humanValidation).not.toContain('>Approved<')
    expect(labels).not.toContain('Approve')
  })

  it('submits expected revision and rationale through the Human Validation API', () => {
    expect(humanValidation).toContain('useHumanValidationApi()')
    expect(humanValidation).toContain('createHumanDecision')
    expect(humanValidation).toContain('buildHumanValidationRequest')
    expect(humanValidation).toContain('expectedGovernanceRevision: props.governance.revision')
    expect(humanValidation).toContain('rationale: rationale.value')
    expect(humanValidation).toContain('submitHumanValidationDecision')
    expect(humanValidation).toContain('refreshCandidate: props.refreshCandidate')
    expect(apiClient).toContain("method: 'POST'")
    expect(apiClient).toContain('body: payload')
    expect(humanValidation).not.toContain('$fetch(')
  })

  it('renders decision history in sequence and TechnicalDebt only from the API', () => {
    expect(humanValidation).toContain('orderedDecisions')
    expect(humanValidation).toContain('left.sequenceNumber - right.sequenceNumber')
    expect(humanValidation).toContain('decision.sequenceNumber')
    expect(humanValidation).toContain('decision.createdAt')
    expect(humanValidation).toContain('decision.rationale')
    expect(humanValidation).toContain('decision.requestedInformation')
    expect(humanValidation).toContain('decision.actorReference')
    expect(humanValidation).toContain('Audit actor')
    expect(humanValidation).toContain('not verified employee identity')
    expect(humanValidation).toContain('View Technical Debt')
    expect(humanValidation).toContain(
      '`/technical-debts/${governance.technicalDebt.technicalDebtId}`',
    )
  })

  it('blocks double submit and shows an in-progress state', () => {
    expect(humanValidation).toContain("requestState.value === 'submitting'")
    expect(humanValidation).toContain(':disabled="isSubmitting"')
    expect(humanValidation).toContain('Submitting Human Validation.')
    expect(humanValidation).toContain('role="status"')
  })

  it('shows 409 conflict and 403 unavailable without inventing a bypass', () => {
    expect(humanValidation).toContain("submitStatus === 'unavailable'")
    expect(humanValidation).toContain('Human Validation is not available.')
    expect(humanValidation).toContain('humanValidationSubmitMessage')
    expect(humanValidation).not.toContain('actor_reference')
    expect(humanValidation).not.toContain('HUMAN_GOVERNANCE')
    expect(humanValidation).not.toContain('v-model="actor')
  })

  it('clears the form and hides retry after a saved decision whose refresh failed', () => {
    expect(humanValidation).toContain("result === 'success-refresh-failed'")
    expect(humanValidation).toContain("submitStatus.value !== 'success-refresh-failed'")
    expect(humanValidation).toContain("submitStatus === 'success-refresh-failed'")
    expect(humanValidation).toContain("humanValidationSubmitMessage('success-refresh-failed')")
    expect(humanValidation).toContain('clearDecisionForm()')
  })

  it('hides Human Validation actions when conflict refresh fails without claiming a save', () => {
    const actionsBlock = humanValidation.slice(
      humanValidation.indexOf('const actionsAvailable'),
      humanValidation.indexOf('const orderedDecisions'),
    )

    expect(actionsBlock).toContain("!== 'unavailable'")
    expect(actionsBlock).toContain("!== 'success-refresh-failed'")
    expect(actionsBlock).toContain("!== 'conflict-refresh-failed'")
    expect(actionsBlock).not.toMatch(/!== 'conflict'(?!-refresh-failed)/)
    expect(humanValidation).toContain("submitStatus === 'conflict-refresh-failed'")
    expect(humanValidation).toContain("humanValidationSubmitMessage('conflict-refresh-failed')")
    expect(humanValidation).toContain("humanValidationSubmitMessage('success-refresh-failed')")
  })

  it('does not include actor, approval, role, provider, or model inputs', () => {
    expect(humanValidationSources).not.toContain('actor_reference')
    expect(humanValidationSources).not.toContain('name="role"')
    expect(humanValidationSources).not.toContain('name="approval"')
    expect(humanValidationSources).not.toContain('authorization')
    expect(humanValidationSources).not.toContain('provider')
    expect(humanValidationSources).not.toContain('model selector')
    expect(humanValidationSources).not.toContain('actor selector')
    expect(humanValidation).not.toContain('type="hidden"')
    expect(humanValidation).not.toMatch(/v-model="(actor|role|approval|provider|model)/)
  })
})
