import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const testsDirectory = dirname(fileURLToPath(import.meta.url))
const frontendAppDirectory = join(testsDirectory, '../../app')

function readFrontendSource(relativePath: string): string {
  return readFileSync(join(frontendAppDirectory, relativePath), 'utf8')
}

const page = readFrontendSource('pages/overview.vue')
const indexPage = readFrontendSource('pages/index.vue')
const reviewList = readFrontendSource('components/overview/OverviewCandidateReviewList.vue')
const operatingModel = readFrontendSource('components/overview/OverviewOperatingModel.vue')
const signalSources = readFrontendSource('components/overview/OverviewSignalSources.vue')
const governance = readFrontendSource('components/overview/OverviewGovernanceBoundary.vue')
const operatingModelCopy = readFrontendSource('utils/overviewOperatingModel.ts')
const governanceCopy = readFrontendSource('utils/overviewGovernanceCopy.ts')
const signalSourceCopy = readFrontendSource('utils/implementedSignalSources.ts')
const apiClient = readFrontendSource('composables/useCandidateApi.ts')
const styles = readFrontendSource('assets/css/main.css')

const overviewSources = [
  page,
  reviewList,
  operatingModel,
  signalSources,
  governance,
  operatingModelCopy,
  governanceCopy,
  signalSourceCopy,
].join('\n')

describe('Overview landing page', () => {
  it('renders the Overview route and redirects / to it', () => {
    expect(page).toContain('id="overview-title"')
    expect(page).toContain('>Overview<')
    expect(page).toContain('Technical debt intelligence and governance')
    expect(indexPage).toContain("navigateTo('/overview')")
  })

  it('loads Candidate collection facts through getCandidates without N+1 Detail requests', () => {
    expect(page).toContain('useCandidateApi()')
    expect(page).toContain('getCandidates')
    expect(page).toContain('toCandidateListItem')
    expect(page).toContain('summarizeCandidateCollection')
    expect(page).toContain('selectCandidatesForReview')
    expect(page).toContain('server: false')
    expect(page).not.toMatch(/\bgetCandidate\b/)
    expect(page).not.toContain('listTechnicalDebts')
    expect(page).not.toContain('getConnectors')
    expect(page).not.toContain('$fetch(')
    expect(page).not.toContain('getMock')
    expect(apiClient).toContain("const CANDIDATES_PATH = '/api/v1/candidates'")
  })

  it('derives collection metrics from list fields with precise represented labels', () => {
    expect(page).toContain('collectionSummary.candidateCount')
    expect(page).toContain('collectionSummary.signalsRepresented')
    expect(page).toContain('collectionSummary.evidenceRepresented')
    expect(page).toContain('Signals represented')
    expect(page).toContain('Evidence represented')
    expect(page).not.toContain('Total signals')
    expect(page).not.toContain('Total evidence')
    expect(page).toContain('current Candidate collection')
  })

  it('does not invent governance-state aggregates or scoring metrics', () => {
    expect(overviewSources).not.toContain('validatedCount')
    expect(overviewSources).not.toContain('pendingCount')
    expect(overviewSources).not.toContain('rejectedCount')
    expect(page).not.toContain('High Risk')
    expect(page).not.toContain('Coverage')
    expect(page).not.toMatch(/\bSLA\b/)
    expect(page).not.toContain('remediation progress')
    expect(page).not.toContain('percentage change')
    expect(reviewList).not.toContain('risk')
    expect(reviewList).not.toContain('severity')
    expect(reviewList).not.toContain('priority')
    expect(reviewList).not.toContain('confidence')
    expect(page).not.toContain('governanceState')
  })

  it('reuses Candidate presentation titles and real Candidate IDs', () => {
    expect(page).toContain('toCandidateListItem')
    expect(reviewList).toContain('candidate.presentationTitle')
    expect(reviewList).toContain('`/candidates/${candidate.id}`')
    expect(reviewList).toContain('Candidate ID {{ candidate.id }}')
    expect(reviewList).toContain('candidate.signalCount')
    expect(reviewList).toContain('candidate.evidenceCount')
    expect(reviewList).toContain('candidate.assetName')
    expect(reviewList).toContain('candidateAssetTypeDisplayLabel(candidate.assetType)')
  })

  it('labels the Candidate subset as reviewable in list order, not recent', () => {
    expect(page).toContain('Candidates for review')
    expect(page).not.toContain('Recent Candidates')
    expect(page).toContain('not priority or recency')
    expect(page).toContain('View all Candidates')
    expect(page).toContain('to="/candidates"')
  })

  it('explains the operating model including Candidate through TechnicalDebt', () => {
    expect(operatingModel).toContain('overviewOperatingModelStages')
    expect(operatingModelCopy).toContain("name: 'Sources'")
    expect(operatingModelCopy).toContain("name: 'Signals & Evidence'")
    expect(operatingModelCopy).toContain("name: 'Correlation'")
    expect(operatingModelCopy).toContain("name: 'Candidate'")
    expect(operatingModelCopy).toContain("name: 'AI Investigation'")
    expect(operatingModelCopy).toContain("name: 'Human Validation'")
    expect(operatingModelCopy).toContain("name: 'TechnicalDebt'")
    expect(operatingModelCopy).toContain('not governed TechnicalDebt before Human Validation')
    expect(operatingModelCopy).toContain('AI is decision support, not governance authority')
    expect(operatingModelCopy).toContain('not live pipeline telemetry')
    expect(operatingModel).toContain('<ol')
    expect(operatingModel).not.toContain('<table')
  })

  it('describes AI as decision support and humans as the governance boundary', () => {
    expect(governanceCopy).toContain('AI investigates. Humans govern.')
    expect(governanceCopy).toContain('AI is decision support, not governance authority')
    expect(governanceCopy).toContain('authoritative governance decision')
    expect(governanceCopy).toContain('VALIDATE')
    expect(governanceCopy).toContain('REJECT')
    expect(governanceCopy).toContain('REQUEST_INFO')
    expect(governanceCopy).toContain('becomes governed TechnicalDebt')
    expect(governanceCopy).toContain('is not validated')
    expect(governanceCopy).toContain('More information is required')
  })

  it('presents implemented ingestion capabilities without inventing source health', () => {
    expect(signalSourceCopy).toContain('Implemented ingestion capability')
    expect(signalSources).toContain('implementedSignalSources')
    expect(signalSourceCopy).toContain("name: 'Semgrep'")
    expect(signalSourceCopy).toContain("name: 'Git'")
    expect(signalSourceCopy).toContain("name: 'Incident management'")
    expect(signalSourceCopy).toContain("name: 'Dependency lifecycle'")
    expect(signalSources).not.toMatch(/\bConnected\b/)
    expect(signalSources).not.toMatch(/\bHealthy\b/)
    expect(signalSources).not.toMatch(/\bLive\b/)
    expect(signalSourceCopy).not.toContain('Last synced')
    expect(signalSourceCopy).not.toContain('github-issues')
    expect(signalSourceCopy).not.toContain('Kafka')
    expect(signalSourceCopy).not.toContain('Jira')
    expect(signalSourceCopy).not.toContain('SonarQube')
  })

  it('keeps Technical Debt and Sources as truthful entry points without fabricated counts', () => {
    expect(page).toContain('to="/technical-debts"')
    expect(page).toContain('View Technical Debts')
    expect(page).toContain('to="/sources"')
    expect(page).toContain('Explore Sources')
    expect(page).not.toContain('technicalDebtCount')
    expect(page).not.toContain('connectorCount')
  })

  it('keeps static workflow and governance content when Candidate data fails', () => {
    expect(page).toContain("candidateViewState === 'error'")
    expect(page).toContain('Candidates could not be loaded.')
    expect(page).toContain('OverviewOperatingModel')
    expect(page).toContain('OverviewSignalSources')
    expect(page).toContain('OverviewGovernanceBoundary')
    expect(page.indexOf('OverviewOperatingModel')).toBeGreaterThan(
      page.indexOf("candidateViewState === 'error'"),
    )
    expect(page).toContain("candidateViewState === 'loading'")
    expect(page).toContain("candidateViewState === 'empty'")
    expect(page).toContain('No Candidates are currently available for review.')
    expect(page).toContain('Loading candidate summary.')
  })

  it('stacks the workflow as a vertical sequence at narrow widths', () => {
    expect(styles).toContain('.overview-workflow')
    expect(styles).toContain('.overview-workflow-stage--branch')
    expect(operatingModel).not.toContain('<table')
    expect(styles).not.toContain('.overview-workflow-table')
  })
})
