import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const testsDirectory = dirname(fileURLToPath(import.meta.url))
const frontendAppDirectory = join(testsDirectory, '../../app')

function readFrontendSource(relativePath: string): string {
  return readFileSync(join(frontendAppDirectory, relativePath), 'utf8')
}

const inventoryPage = readFrontendSource('pages/technical-debts/index.vue')
const detailPage = readFrontendSource('pages/technical-debts/[id].vue')
const table = readFrontendSource('components/technicalDebt/TechnicalDebtPortfolioTable.vue')
const detailHeader = readFrontendSource(
  'components/technicalDebt/TechnicalDebtDetailHeader.vue',
)
const humanValidation = readFrontendSource(
  'components/candidate/CandidateHumanValidation.vue',
)
const apiClient = readFrontendSource('composables/useTechnicalDebtApi.ts')
const mapper = readFrontendSource('utils/mapTechnicalDebt.ts')
const copy = readFrontendSource('utils/technicalDebtPageCopy.ts')
const styles = readFrontendSource('assets/css/main.css')

const inventorySources = `${inventoryPage}\n${table}\n${copy}`
const detailSources = `${detailPage}\n${detailHeader}\n${copy}`

const inventedProductFields = [
  /\bRisk\b/,
  /\bEffort\b/,
  /\bOwner\b/,
  /\bseverity\b/i,
  /\bpriority\b/i,
  /\bremediation\b/i,
  /\bassignee\b/i,
  /\bdue date\b/i,
  /\bSLA\b/,
  /\bconfidence\b/i,
  /\baccepted risk\b/i,
]

describe('TechnicalDebt inventory page', () => {
  it('loads the inventory through useTechnicalDebtApi.listTechnicalDebts', () => {
    expect(inventoryPage).toContain('useTechnicalDebtApi()')
    expect(inventoryPage).toContain('listTechnicalDebts')
    expect(inventoryPage).toContain('toTechnicalDebtListItem')
    expect(inventoryPage).toContain('server: false')
    expect(apiClient).toContain("const TECHNICAL_DEBTS_PATH = '/api/v1/technical-debts'")
    expect(inventoryPage).not.toContain('$fetch(')
    expect(inventoryPage).not.toContain('getMock')
    expect(inventoryPage).not.toContain('getCandidates')
    expect(inventoryPage).not.toMatch(/\bgetCandidate\b/)
    expect(inventoryPage).not.toContain('getTechnicalDebt')
  })

  it('does not fetch Candidate Detail to decorate inventory rows', () => {
    expect(table).not.toMatch(/\bgetCandidate\b/)
    expect(table).not.toContain('useCandidateApi')
    expect(table).not.toContain('/api/v1/candidates/')
    expect(mapper).toContain('summary.source_candidate_id')
    expect(mapper).toContain('summary.hypothesis')
    expect(inventoryPage).not.toContain('getCandidate(')
  })

  it('renders a compact governed-record header without Candidate Pool framing', () => {
    expect(copy).toContain("export const technicalDebtsPageTitle = 'Technical Debts'")
    expect(copy).toContain(
      'Governed technical-debt records created through Human Validation.',
    )
    expect(copy).toContain(
      'Candidates appear here only after a persisted VALIDATE decision.',
    )
    expect(inventoryPage).toContain('id="technical-debts-title"')
    expect(inventoryPage).toContain('page-header--queue')
    expect(inventorySources).not.toContain('Technical Debt Governance')
    expect(inventorySources).not.toContain('TechnicalDebt portfolio')
    expect(inventorySources).not.toContain('This portfolio is not a remediation plan')
    expect(inventoryPage).not.toContain('candidate-review-queue')
    expect(table).not.toContain('Candidate Pool')
  })

  it('renders inventory, empty, loading, and error states without fake lifecycle UI', () => {
    expect(inventoryPage).toContain('TechnicalDebtPortfolioTable')
    expect(copy).toContain('No TechnicalDebt records have been created yet.')
    expect(copy).toContain(
      'TechnicalDebt records are created when a human reviewer validates a Candidate.',
    )
    expect(copy).toContain('Review Candidates')
    expect(inventoryPage).toContain('to="/candidates"')
    expect(copy).toContain('Loading Technical Debts.')
    expect(copy).toContain('Technical Debts could not be loaded.')
    expect(inventoryPage).toContain('technicalDebtsInventoryLoading')
    expect(inventoryPage).toContain('technicalDebtsInventoryError')
    expect(inventoryPage).toContain('technicalDebtsInventoryEmptyTitle')
    expect(inventoryPage).toContain('technicalDebtsInventoryEmptyExplanation')
    expect(inventoryPage).toContain('technicalDebtsReviewCandidatesLabel')
    expect(inventorySources).toContain('Loading Technical Debts.')
    expect(inventorySources).toContain('Technical Debts could not be loaded.')
    expect(inventoryPage).toContain("viewState === 'ready'")
    expect(inventoryPage).toContain("viewState === 'empty'")
    expect(inventoryPage).toContain("viewState === 'loading'")
    expect(inventoryPage).toContain("viewState === 'error'")
    expect(inventoryPage).toContain('role="status"')
    expect(inventoryPage).toContain('role="alert"')
    expect(inventorySources).not.toContain('In remediation')
    expect(inventorySources).not.toContain('Accepted risk')
    expect(table).not.toContain('lifecycleStatus')
    expect(table).not.toContain('Open</span>')
    expect(table).not.toContain('Active')
    expect(table).not.toContain('Resolved')
  })

  it('presents persisted TechnicalDebt fields and Candidate provenance from the list API', () => {
    expect(table).toContain('`/technical-debts/${item.technicalDebtId}`')
    expect(table).toContain('Open TechnicalDebt')
    expect(table).toContain('Open Candidate')
    expect(table).toContain('`/candidates/${item.sourceCandidateId}`')
    expect(table).toContain('technicalDebtPresentationTitle(item.hypothesis)')
    expect(table).toContain('item.canonicalAssetKey')
    expect(table).toContain('item.canonicalAssetType')
    expect(table).toContain('formatDisplayTimestamp(item.createdAt)')
    expect(table).toContain('TechnicalDebt ID {{ item.technicalDebtId }}')
    expect(table).toContain('Candidate ID {{ item.sourceCandidateId }}')
    expect(table).toContain('class="visually-hidden"')
    expect(table).toContain('<table')
    expect(table).toContain('<th scope="col">')
    expect(table).toContain('scope="row"')
    expect(table).not.toContain('Parent issue')
    expect(table).not.toContain('Original TechnicalDebt')
    expect(table).not.toContain('AI finding')
  })

  it('does not invent unavailable product fields or governance write actions', () => {
    for (const pattern of inventedProductFields) {
      expect(inventorySources).not.toMatch(pattern)
    }
    expect(table).not.toContain('Resolve')
    expect(table).not.toContain('Fix')
    expect(table).not.toContain('Accept risk')
    expect(table).not.toContain('Assign')
    expect(table).not.toContain('Remediate')
    expect(inventoryPage).not.toContain('submitHumanValidation')
    expect(inventoryPage).not.toContain('postHuman')
  })

  it('stacks the inventory at narrow widths without forcing table overflow', () => {
    expect(styles).toContain('.technical-debt-table')
    expect(styles).toContain('.technical-debt-table-wrapper')
    expect(styles).toContain('overflow-x: visible')
    expect(styles).toContain('.technical-debt-table thead')
    expect(styles).toContain('max-width: 51.99rem')
    expect(table).toContain('technical-debt-table')
    expect(table).toContain('candidate-link')
  })
})

describe('TechnicalDebt detail page', () => {
  it('renders TechnicalDebt facts, source Candidate, and creation VALIDATE decision', () => {
    expect(detailPage).toContain('useTechnicalDebtApi()')
    expect(detailPage).toContain('getTechnicalDebt')
    expect(detailHeader).toContain('presentation.technicalDebtId')
    expect(detailHeader).toContain('presentation.lifecycleStatus')
    expect(detailHeader).toContain('presentation.createdAt')
    expect(detailPage).toContain('presentation.sourceCandidate.candidateId')
    expect(detailPage).toContain('presentation.sourceCandidate.hypothesis')
    expect(detailPage).toContain('presentation.sourceCandidate.canonicalAssetKey')
    expect(detailPage).toContain('presentation.sourceCandidate.correlationRationale')
    expect(detailPage).toContain('presentation.creationHumanDecision.decision')
    expect(detailPage).toContain('presentation.creationHumanDecision.sequenceNumber')
    expect(detailPage).toContain('presentation.creationHumanDecision.rationale')
    expect(detailPage).toContain('presentation.creationHumanDecision.createdAt')
    expect(detailPage).toContain('presentation.creationHumanDecision.actorReference')
    expect(detailPage).toContain('Audit actor')
    expect(detailSources).not.toContain('CandidateEvidenceList')
    expect(detailSources).not.toContain('Validated by')
    expect(detailSources).not.toContain('Approved by')
    for (const pattern of inventedProductFields) {
      expect(detailSources).not.toMatch(pattern)
    }
  })

  it('links back to the source Candidate and inventory using returned identifiers', () => {
    expect(detailHeader).toContain('to="/technical-debts"')
    expect(detailPage).toContain('to="/technical-debts"')
    expect(detailPage).toContain('Open Candidate')
    expect(detailPage).toContain(
      '`/candidates/${presentation.sourceCandidate.candidateId}`',
    )
    expect(humanValidation).toContain(
      '`/technical-debts/${governance.technicalDebt.technicalDebtId}`',
    )
    expect(detailHeader).toContain('Technical identifiers')
    expect(detailPage).toContain('Technical details')
  })

  it('handles unknown and invalid identifiers without exposing raw HTTP language', () => {
    expect(detailPage).toContain("viewState === 'not-found'")
    expect(detailPage).toContain("viewState === 'invalid-identifier'")
    expect(detailPage).toContain("viewState === 'error'")
    expect(copy).toContain('TechnicalDebt was not found.')
    expect(copy).toContain('The TechnicalDebt identifier is invalid.')
    expect(copy).toContain('TechnicalDebt details could not be loaded.')
    expect(detailPage).toContain('technicalDebtsDetailNotFoundTitle')
    expect(detailPage).toContain('technicalDebtsDetailInvalidTitle')
    expect(detailPage).toContain('technicalDebtsDetailErrorTitle')
    expect(detailPage).not.toContain('statusCode')
    expect(detailPage).not.toContain('HTTP 404')
    expect(detailPage).not.toContain('SQL')
  })

  it('does not introduce governance write actions on the detail page', () => {
    expect(detailPage).not.toContain('Resolve')
    expect(detailPage).not.toContain('Fix')
    expect(detailPage).not.toContain('Accept risk')
    expect(detailPage).not.toContain('Assign')
    expect(detailPage).not.toContain('Remediate')
    expect(detailPage).not.toContain('submitHumanValidation')
  })
})
