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
const tabDefs = readFrontendSource('utils/candidateDetailTabs.ts')
const overviewTab = readFrontendSource('components/candidate/CandidateOverviewTab.vue')
const evidenceTab = readFrontendSource('components/candidate/CandidateEvidenceContextTab.vue')
const summaryCard = readFrontendSource('components/candidate/CandidateSummaryCard.vue')
const correlation = readFrontendSource('components/candidate/CandidateCorrelationSummary.vue')
const enterpriseSnapshot = readFrontendSource(
  'components/candidate/CandidateEnterpriseSnapshot.vue',
)
const dependencySummary = readFrontendSource(
  'components/candidate/CandidateDependencySummary.vue',
)
const evidenceList = readFrontendSource('components/candidate/CandidateEvidenceList.vue')
const evidenceItem = readFrontendSource('components/candidate/CandidateEvidenceItem.vue')
const signalList = readFrontendSource('components/candidate/CandidateSignalList.vue')
const signalItem = readFrontendSource('components/candidate/CandidateSignalItem.vue')
const provenance = readFrontendSource('components/candidate/CandidateProvenanceDetails.vue')
const enterpriseContext = readFrontendSource(
  'components/candidate/CandidateEnterpriseContext.vue',
)
const dependencyContext = readFrontendSource(
  'components/candidate/CandidateDependencyContext.vue',
)
const dependencyAssetList = readFrontendSource(
  'components/candidate/CandidateDependencyAssetList.vue',
)
const agentInvestigation = readFrontendSource(
  'components/candidate/CandidateAgentInvestigation.vue',
)
const humanValidation = readFrontendSource(
  'components/candidate/CandidateHumanValidation.vue',
)

const candidateDetailSources = [
  detailPage,
  header,
  tabs,
  overviewTab,
  evidenceTab,
  evidenceList,
  signalList,
  enterpriseContext,
  dependencyContext,
  agentInvestigation,
  humanValidation,
].join('\n')

describe('Candidate Detail information architecture', () => {
  it('keeps a stable header with identity context across tabs', () => {
    expect(detailPage).toContain('CandidateDetailHeader')
    expect(header).toContain('Candidates')
    expect(header).toContain('aria-current="page">Candidate')
    expect(header).toContain('id="candidate-title"')
    expect(header).toContain('{{ title }}')
    expect(header).toContain('asset.name')
    expect(header).toContain('candidateGovernanceStateLabels[governance.state]')
    expect(header).toContain('candidatePoolAssetTypeLabels[asset.assetType]')
    expect(header).toContain('candidateAssetCriticalityLabels[asset.criticality]')
    expect(header).toContain('candidateAssetLifecycleStatusLabels[asset.lifecycleStatus]')
    expect(header).toContain('candidate.candidateId')
    expect(header).toContain('Technical identifiers')
    expect(header).toContain('candidateGovernanceDistinctionNotice')
    expect(header).toContain("governance.state !== 'VALIDATED'")
    expect(header).toContain('canonicalProblemType')
  })

  it('uses real content tabs instead of in-page section anchors', () => {
    expect(detailPage).toContain('CandidateDetailTabs')
    expect(detailPage).toContain('parseCandidateDetailTab(route.query.tab)')
    expect(detailPage).toContain("selectTab('investigation')")
    expect(tabs).toContain('role="tablist"')
    expect(tabs).toContain('role="tab"')
    expect(tabs).toContain(':aria-selected="selectedTab === tab.id"')
    expect(tabs).toContain(':aria-controls="tab.panelId"')
    expect(tabs).toContain('ArrowRight')
    expect(tabDefs).toContain("label: 'Overview'")
    expect(tabDefs).toContain("label: 'Evidence & Context'")
    expect(tabDefs).toContain("label: 'AI Investigation'")
    expect(tabDefs).toContain("label: 'Human Validation'")
    expect(detailPage).not.toContain(':href="`#${section.id}`"')
    expect(detailPage).not.toContain('candidate-history')
  })

  it('renders only the selected major workflow while keeping investigation and validation mounted', () => {
    expect(detailPage).toContain('role="tabpanel"')
    expect(detailPage).toContain(":hidden=\"selectedTab !== 'overview'\"")
    expect(detailPage).toContain(":hidden=\"selectedTab !== 'evidence'\"")
    expect(detailPage).toContain(':isActive="selectedTab === \'investigation\'"')
    expect(detailPage).toContain(':isActive="selectedTab === \'validation\'"')
    expect(agentInvestigation).toContain(':hidden="!isActive"')
    expect(humanValidation).toContain(':hidden="!isActive"')
    expect(detailPage).not.toContain('v-if="selectedTab')
  })

  it('groups concise identity and rationale content under Overview', () => {
    expect(detailPage).toContain('id="candidate-overview"')
    expect(detailPage).toContain('CandidateOverviewTab')
    expect(overviewTab).toContain('CandidateSummaryCard')
    expect(overviewTab).toContain('CandidateCorrelationSummary')
    expect(overviewTab).toContain('CandidateEnterpriseSnapshot')
    expect(overviewTab).toContain('CandidateDependencySummary')
    expect(overviewTab).toContain('Open AI Investigation')
    expect(overviewTab).not.toContain('CandidateEvidenceList')
    expect(overviewTab).not.toContain('CandidateSignalList')
    expect(summaryCard).toContain('Candidate summary')
    expect(summaryCard).toContain('problemLabel')
    expect(summaryCard).toContain('candidate.assetDisplayName')
    expect(correlation).toContain('Correlation explanation')
    expect(correlation).toContain('System-generated correlation, not validation.')
    expect(enterpriseSnapshot).toContain('Enterprise snapshot')
    expect(dependencySummary).toContain('Dependency snapshot')
  })

  it('groups detailed evidence, provenance, and context under Evidence & Context', () => {
    expect(detailPage).toContain('id="candidate-evidence-context"')
    expect(detailPage).toContain('CandidateEvidenceContextTab')
    expect(evidenceTab).toContain('CandidateEvidenceList')
    expect(evidenceTab).toContain('CandidateSignalList')
    expect(evidenceTab).toContain('CandidateEnterpriseContext')
    expect(evidenceTab).toContain('CandidateDependencyContext')
    expect(evidenceList).toContain('>Evidence<')
    expect(signalList).toContain('>Signals<')
    expect(evidenceItem).toContain('Source reference')
    expect(signalItem).toContain('Signal type')
    expect(provenance).toContain('Technical details')
    expect(evidenceItem).toContain('CandidateProvenanceDetails')
    expect(signalItem).toContain('CandidateProvenanceDetails')
    expect(enterpriseContext).toContain('Enterprise context')
    expect(dependencyContext).toContain('Dependencies')
  })

  it('places AI Investigation after Evidence & Context and Human Validation after investigation', () => {
    expect(agentInvestigation).toContain('id="candidate-agent-investigation"')
    expect(detailPage).toContain('CandidateAgentInvestigation')
    expect(agentInvestigation).toContain('AI Investigation')
    expect(humanValidation).toContain('id="candidate-human-validation"')
    expect(detailPage).toContain('CandidateHumanValidation')
    expect(humanValidation).toContain('Human Validation')

    const overviewStart = detailPage.indexOf('id="candidate-overview"')
    const evidenceStart = detailPage.indexOf('id="candidate-evidence-context"')
    const investigationStart = detailPage.indexOf('CandidateAgentInvestigation')
    const validationStart = detailPage.indexOf('CandidateHumanValidation')
    expect(overviewStart).toBeGreaterThan(-1)
    expect(evidenceStart).toBeGreaterThan(overviewStart)
    expect(investigationStart).toBeGreaterThan(evidenceStart)
    expect(validationStart).toBeGreaterThan(investigationStart)

    expect(detailPage).not.toContain('candidate-history')
    expect(candidateDetailSources).not.toMatch(/coming soon/i)
    expect(candidateDetailSources).not.toMatch(/agent analysis/i)
    expect(candidateDetailSources).not.toMatch(/audit event/i)
  })

  it('keeps empty dependency states compact', () => {
    expect(dependencyAssetList).toContain('None recorded.')
    expect(dependencySummary).toContain('CandidateDependencyAssetList')
    expect(dependencyContext).toContain('CandidateDependencyAssetList')
    expect(dependencyContext).not.toContain('candidate-context-panel')
    expect(dependencySummary).not.toContain('candidate-context-grid')
  })

  it('keeps Candidate Detail on the real Candidate API without a mock fallback', () => {
    expect(detailPage).toContain('useCandidateApi()')
    expect(detailPage).toContain('getCandidate')
    expect(detailPage).not.toContain('getMockCandidateDetail')
    expect(detailPage).not.toContain('getCandidates')
  })
})
