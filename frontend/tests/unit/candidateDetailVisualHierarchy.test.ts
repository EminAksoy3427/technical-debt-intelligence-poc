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
const header = readFrontendSource('components/candidate/CandidateDetailHeader.vue')
const tabs = readFrontendSource('components/candidate/CandidateDetailTabs.vue')
const overviewTab = readFrontendSource('components/candidate/CandidateOverviewTab.vue')
const summaryCard = readFrontendSource('components/candidate/CandidateSummaryCard.vue')
const evidenceItem = readFrontendSource('components/candidate/CandidateEvidenceItem.vue')
const signalItem = readFrontendSource('components/candidate/CandidateSignalItem.vue')
const provenance = readFrontendSource('components/candidate/CandidateProvenanceDetails.vue')
const dependencyAssetList = readFrontendSource(
  'components/candidate/CandidateDependencyAssetList.vue',
)
const dependencySummary = readFrontendSource(
  'components/candidate/CandidateDependencySummary.vue',
)
const dependencyContext = readFrontendSource(
  'components/candidate/CandidateDependencyContext.vue',
)
const agentInvestigation = readFrontendSource(
  'components/candidate/CandidateAgentInvestigation.vue',
)
const humanValidation = readFrontendSource(
  'components/candidate/CandidateHumanValidation.vue',
)
const display = readFrontendSource('utils/candidateDetailDisplay.ts')
const styles = readFrontendSource('assets/css/main.css')

describe('Candidate Detail visual hierarchy', () => {
  it('keeps the human-readable presentation title and Candidate versus TechnicalDebt meaning', () => {
    expect(detailPage).toContain('resolveCandidatePresentationTitle')
    expect(header).toContain('{{ title }}')
    expect(header).toContain('asset.name')
    expect(header).toContain('candidateGovernanceDistinctionNotice')
    expect(display).toContain('Candidate awaiting human validation. Not TechnicalDebt.')
    expect(display).toContain('This Candidate was rejected and is not TechnicalDebt.')
    expect(header).toContain("governance.state !== 'VALIDATED'")
  })

  it('keeps raw identifiers accessible through disclosure instead of the primary header', () => {
    expect(header).toContain('Technical identifiers')
    expect(header).toContain('candidate.candidateId')
    expect(header).toContain('canonicalProblemType')
    expect(header).toContain('CandidateProvenanceDetails')
    expect(header).not.toContain('class="candidate-header-id"')
    expect(provenance).toContain('summaryLabel')
    expect(evidenceItem).toContain('Evidence ID')
    expect(evidenceItem).toContain('Source reference')
    expect(signalItem).toContain('Signal ID')
    expect(signalItem).toContain('Source record ID')
  })

  it('renders Overview from actual source, signal, and evidence values', () => {
    expect(summaryCard).toContain('problemLabel')
    expect(summaryCard).toContain('candidate.assetDisplayName')
    expect(summaryCard).toContain('uniqueSourceSystems')
    expect(summaryCard).toContain('formatSourceSystemLabel')
    expect(summaryCard).toContain('signals.length')
    expect(summaryCard).toContain('evidence.length')
    expect(summaryCard).not.toContain('risk score')
    expect(overviewTab).toContain('presentation.candidate.correlationRationale')
  })

  it('keeps dependency empty values compact and truthful', () => {
    expect(dependencyAssetList).toContain('None recorded.')
    expect(dependencyAssetList).toContain('candidate-empty-value')
    expect(dependencySummary).toContain('directDependents')
    expect(dependencySummary).toContain('reachableDependents')
    expect(dependencyContext).toContain('CandidateDependencyAssetList')
    expect(dependencyContext).toContain(
      'Reachability represents graph connectivity and does not imply guaranteed operational impact or outage.',
    )
  })

  it('preserves tab routing and investigation/validation mount behavior', () => {
    expect(detailPage).toContain('parseCandidateDetailTab(route.query.tab)')
    expect(tabs).toContain('role="tablist"')
    expect(tabs).toContain('role="tab"')
    expect(detailPage).toContain(':isActive="selectedTab === \'investigation\'"')
    expect(detailPage).toContain(':isActive="selectedTab === \'validation\'"')
    expect(agentInvestigation).toContain(':hidden="!isActive"')
    expect(humanValidation).toContain(':hidden="!isActive"')
    expect(detailPage).not.toContain('v-if="selectedTab')
    expect(agentInvestigation).toContain('Start Investigation')
    expect(humanValidation).toContain('humanValidationSubmitLabel')
  })

  it('uses Candidate Detail presentation primitives without nested cards', () => {
    expect(styles).toContain('.candidate-section-surface')
    expect(styles).toContain('.candidate-chip-row')
    expect(styles).toContain('.candidate-metric-row')
    expect(styles).toContain('.candidate-kv-row')
    expect(styles).toContain('.candidate-type-badge')
    expect(styles).toContain('.candidate-helper')
    expect(overviewTab).toContain('candidate-section-surface')
    expect(overviewTab).not.toContain('candidate-context-panel')
    expect(header).not.toContain('candidate-summary-facts')
  })
})
