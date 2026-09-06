import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const testsDirectory = dirname(fileURLToPath(import.meta.url))
const frontendAppDirectory = join(testsDirectory, '../../app')

function readFrontendSource(relativePath: string): string {
  return readFileSync(join(frontendAppDirectory, relativePath), 'utf8')
}

const portfolioPage = readFrontendSource('pages/technical-debts/index.vue')
const detailPage = readFrontendSource('pages/technical-debts/[id].vue')
const table = readFrontendSource('components/technicalDebt/TechnicalDebtPortfolioTable.vue')
const humanValidation = readFrontendSource(
  'components/candidate/CandidateHumanValidation.vue',
)
const apiClient = readFrontendSource('composables/useTechnicalDebtApi.ts')

const portfolioSources = `${portfolioPage}\n${table}`
const detailSources = detailPage

describe('TechnicalDebt portfolio page', () => {
  it('loads the portfolio through useTechnicalDebtApi.listTechnicalDebts', () => {
    expect(portfolioPage).toContain('useTechnicalDebtApi()')
    expect(portfolioPage).toContain('listTechnicalDebts')
    expect(portfolioPage).toContain('toTechnicalDebtListItem')
    expect(portfolioPage).toContain('server: false')
    expect(apiClient).toContain("const TECHNICAL_DEBTS_PATH = '/api/v1/technical-debts'")
    expect(portfolioPage).not.toContain('$fetch(')
    expect(portfolioPage).not.toContain('getMock')
  })

  it('renders list, empty, and loading states without risk, effort, or owner UI', () => {
    expect(portfolioPage).toContain('TechnicalDebtPortfolioTable')
    expect(portfolioPage).toContain('No validated TechnicalDebt records exist yet.')
    expect(portfolioPage).toContain('Loading Technical Debts.')
    expect(portfolioPage).toContain("viewState === 'ready'")
    expect(portfolioPage).toContain("viewState === 'empty'")
    expect(table).toContain('`/technical-debts/${item.technicalDebtId}`')
    expect(table).toContain('item.hypothesis')
    expect(table).toContain('item.canonicalAssetKey')
    expect(table).toContain('item.lifecycleStatus')
    expect(table).toContain('item.createdAt')
    expect(portfolioSources).not.toMatch(/\bRisk\b/)
    expect(portfolioSources).not.toMatch(/\bEffort\b/)
    expect(portfolioSources).not.toMatch(/\bOwner\b/)
    expect(portfolioSources).not.toContain('priority')
    expect(portfolioSources).not.toContain('target date')
  })
})

describe('TechnicalDebt detail page', () => {
  it('renders TechnicalDebt facts, source Candidate, and creation VALIDATE decision', () => {
    expect(detailPage).toContain('useTechnicalDebtApi()')
    expect(detailPage).toContain('getTechnicalDebt')
    expect(detailPage).toContain('presentation.technicalDebtId')
    expect(detailPage).toContain('presentation.lifecycleStatus')
    expect(detailPage).toContain('presentation.createdAt')
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
    expect(detailSources).not.toMatch(/\bRisk\b/)
    expect(detailSources).not.toMatch(/\bEffort\b/)
    expect(detailSources).not.toMatch(/\bOwner\b/)
  })

  it('links back to the source Candidate and portfolio using returned identifiers', () => {
    expect(detailPage).toContain('Back to Technical Debts')
    expect(detailPage).toContain('to="/technical-debts"')
    expect(detailPage).toContain('View source Candidate')
    expect(detailPage).toContain('`/candidates/${presentation.sourceCandidate.candidateId}`')
    expect(humanValidation).toContain(
      '`/technical-debts/${governance.technicalDebt.technicalDebtId}`',
    )
  })

  it('handles unknown and invalid identifiers using Candidate Detail conventions', () => {
    expect(detailPage).toContain("viewState === 'not-found'")
    expect(detailPage).toContain("viewState === 'invalid-identifier'")
    expect(detailPage).toContain("viewState === 'error'")
    expect(detailPage).toContain('TechnicalDebt was not found.')
    expect(detailPage).toContain('The TechnicalDebt identifier is invalid.')
    expect(detailPage).toContain('TechnicalDebt details could not be loaded.')
  })
})
