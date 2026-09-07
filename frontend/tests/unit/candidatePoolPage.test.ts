import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const testsDirectory = dirname(fileURLToPath(import.meta.url))
const frontendAppDirectory = join(testsDirectory, '../../app')

function readFrontendSource(relativePath: string): string {
  return readFileSync(join(frontendAppDirectory, relativePath), 'utf8')
}

const page = readFrontendSource('pages/candidates/index.vue')
const table = readFrontendSource('components/candidate/CandidatePoolTable.vue')
const mapper = readFrontendSource('utils/mapCandidateSummary.ts')
const apiClient = readFrontendSource('composables/useCandidateApi.ts')
const filters = readFrontendSource('utils/filterCandidates.ts')
const styles = readFrontendSource('assets/css/main.css')
const poolSources = `${page}\n${table}\n${mapper}`

describe('Candidate Pool review queue', () => {
  it('loads the pool through getCandidates without Candidate Detail N+1 requests', () => {
    expect(page).toContain('useCandidateApi()')
    expect(page).toContain('getCandidates')
    expect(page).toContain('toCandidateListItem')
    expect(page).toContain('server: false')
    expect(page).not.toMatch(/\bgetCandidate\b/)
    expect(page).not.toContain('$fetch(')
    expect(page).not.toContain('getMock')
    expect(apiClient).toContain("const CANDIDATES_PATH = '/api/v1/candidates'")
    expect(mapper).toContain('resolveCandidatePresentationTitle')
    expect(mapper).toContain('signalTypes: []')
  })

  it('renders a compact Candidates header without repeating pool caveats', () => {
    expect(page).toContain('id="candidates-title"')
    expect(page).toContain('>Candidates<')
    expect(page).toContain(
      'Review correlated technical-debt Candidates before they become governed',
    )
    expect(page).toContain('TechnicalDebt records.')
    expect(page).not.toContain('Candidate Pool')
    expect(page).not.toContain('Technical Debt Governance')
    expect(page).not.toContain('Candidates are not validated TechnicalDebt records.')
    expect(table).not.toContain('Candidates are not validated TechnicalDebt records.')
  })

  it('preserves search and asset-type filters and adds client-side reset', () => {
    expect(page).toContain('Search candidates')
    expect(page).toContain('Hypothesis or asset name')
    expect(page).toContain('Asset type')
    expect(page).toContain('All asset types')
    expect(page).toContain('candidatePoolAssetTypeLabels')
    expect(page).toContain('v-model="search"')
    expect(page).toContain('v-model="assetType"')
    expect(page).toContain('filterCandidates')
    expect(page).toContain('areCandidateFiltersActive')
    expect(page).toContain('function clearFilters')
    expect(page).toContain('Reset')
    expect(page).toContain('Clear filters')
    expect(page).not.toContain('reviewStatus')
    expect(page).not.toContain('governanceState')
    expect(filters).toContain('candidate.title.toLowerCase()')
    expect(filters).toContain('candidate.presentationTitle.toLowerCase()')
    expect(filters).toContain('candidate.assetName.toLowerCase()')
    expect(filters).toContain('candidate.assetType === filters.assetType')
  })

  it('uses a human-readable Candidate title instead of the UUID as the primary label', () => {
    expect(table).toContain('candidate.presentationTitle')
    expect(table).toContain('class="candidate-title"')
    expect(table).toContain('Candidate ID {{ candidate.id }}')
    expect(table).toContain('class="visually-hidden"')
    expect(table).not.toContain('class="candidate-identifier"')
    expect(table).not.toMatch(/CND-/)
  })

  it('shows the affected asset, recorded counts, and Open Candidate action', () => {
    expect(table).toContain('Affected asset')
    expect(table).toContain('candidate.assetName')
    expect(table).toContain('candidateAssetTypeDisplayLabel(candidate.assetType)')
    expect(table).toContain('candidate.signalCount')
    expect(table).toContain('candidate.evidenceCount')
    expect(table).toContain('Open Candidate')
    expect(table).toContain('`/candidates/${candidate.id}`')
    expect(table).toContain('<table')
    expect(table).toContain('<th scope="col">')
    expect(table).toContain('scope="row"')
    expect(table).not.toContain('Investigate')
    expect(table).not.toContain('Validate')
    expect(table).not.toContain('Reject')
    expect(table).not.toContain('Fix')
  })

  it('does not present Candidates as TechnicalDebt or invent unavailable list fields', () => {
    expect(poolSources).not.toMatch(/\bTechnicalDebt\b.*row/)
    expect(table).not.toContain('governance')
    expect(table).not.toContain('PENDING')
    expect(table).not.toContain('VALIDATED')
    expect(table).not.toContain('REJECTED')
    expect(table).not.toContain('Semgrep')
    expect(table).not.toContain('sourceSystem')
    expect(table).not.toContain('risk')
    expect(table).not.toContain('priority')
    expect(table).not.toContain('confidence')
    expect(table).not.toContain('severity')
    expect(table).not.toContain('effort')
    expect(table).not.toContain('SLA')
    expect(table).not.toContain('due date')
    expect(table).not.toContain('owner')
    expect(page).not.toContain('getCandidate(')
  })

  it('keeps loading, error, empty, and filtered-empty states', () => {
    expect(page).toContain("viewState === 'loading'")
    expect(page).toContain("viewState === 'error'")
    expect(page).toContain("viewState === 'empty'")
    expect(page).toContain("viewState === 'filtered-empty'")
    expect(page).toContain('Loading candidates.')
    expect(page).toContain('Candidates could not be loaded.')
    expect(page).toContain('No Candidates are currently available.')
    expect(page).toContain('No Candidates match the current filters.')
    expect(page).toContain('role="status"')
    expect(page).toContain('role="alert"')
    expect(page).toContain('@click="clearFilters"')
  })

  it('stacks the review queue at narrow widths without forcing table overflow', () => {
    expect(styles).toContain('.candidate-table--queue')
    expect(styles).toContain('.candidate-table-wrapper--queue')
    expect(styles).toContain('max-width: 51.99rem')
    expect(styles).toContain('.candidate-table--queue thead')
    expect(table).toContain('candidate-table--queue')
    expect(table).toContain('candidate-link')
  })
})
