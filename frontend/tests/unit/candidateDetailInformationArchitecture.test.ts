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
const evidenceList = readFrontendSource('components/candidate/CandidateEvidenceList.vue')
const signalList = readFrontendSource('components/candidate/CandidateSignalList.vue')
const enterpriseContext = readFrontendSource(
  'components/candidate/CandidateEnterpriseContext.vue',
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

const candidateDetailSources = [
  detailPage,
  evidenceList,
  signalList,
  enterpriseContext,
  dependencyContext,
  agentInvestigation,
  humanValidation,
].join('\n')

describe('Candidate Detail information architecture', () => {
  it('groups existing identity and rationale content under Overview', () => {
    expect(detailPage).toContain('id="candidate-overview"')
    expect(detailPage).toContain('>Overview<')
    expect(detailPage).toContain('presentation.candidate.hypothesis')
    expect(detailPage).toContain('presentation.candidate.candidateId')
    expect(detailPage).toContain('presentation.candidate.assetDisplayName')
    expect(detailPage).toContain('presentation.candidate.canonicalAssetKey')
    expect(detailPage).toContain('presentation.candidate.correlationRationale')
    expect(detailPage).toContain('This is a Candidate, not validated TechnicalDebt.')

    const overviewStart = detailPage.indexOf('id="candidate-overview"')
    const evidenceContextStart = detailPage.indexOf('id="candidate-evidence-context"')
    const overviewBlock = detailPage.slice(overviewStart, evidenceContextStart)

    expect(overviewStart).toBeGreaterThan(-1)
    expect(evidenceContextStart).toBeGreaterThan(overviewStart)
    expect(overviewBlock).toContain('presentation.candidate.hypothesis')
    expect(overviewBlock).toContain('Correlation rationale')
    expect(overviewBlock).not.toContain('CandidateEvidenceList')
    expect(overviewBlock).not.toContain('CandidateSignalList')
  })

  it('groups existing evidence and context content under Evidence & Context', () => {
    expect(detailPage).toContain('id="candidate-evidence-context"')
    expect(detailPage).toContain('Evidence &amp; Context')

    const evidenceContextStart = detailPage.indexOf('id="candidate-evidence-context"')
    const evidenceContextBlock = detailPage.slice(evidenceContextStart)

    expect(evidenceContextBlock).toContain('CandidateEvidenceList')
    expect(evidenceContextBlock).toContain('CandidateSignalList')
    expect(evidenceContextBlock).toContain('CandidateEnterpriseContext')
    expect(evidenceContextBlock).toContain('CandidateDependencyContext')
    expect(evidenceList).toContain('>Evidence<')
    expect(signalList).toContain('>Signals<')
    expect(enterpriseContext).toContain('Enterprise context')
    expect(enterpriseContext).toContain('Enterprise asset ownership')
    expect(enterpriseContext).toContain('Direct incidents')
    expect(dependencyContext).toContain('Dependency context')
  })

  it('offers local navigation only for implemented sections', () => {
    expect(detailPage).toContain('aria-label="Candidate sections"')
    expect(detailPage).toContain(':href="`#${section.id}`"')
    expect(detailPage).toContain("id: 'candidate-overview'")
    expect(detailPage).toContain("id: 'candidate-evidence-context'")
    expect(detailPage).toContain("id: 'candidate-agent-investigation'")
    expect(detailPage).toContain("id: 'candidate-human-validation'")
    expect(detailPage).toContain("label: 'Overview'")
    expect(detailPage).toContain("label: 'Evidence & Context'")
    expect(detailPage).toContain("label: 'Agent Investigation'")
    expect(detailPage).toContain("label: 'Human Validation'")
    expect(detailPage).not.toContain('candidate-history')
  })

  it('places Agent Investigation after Evidence & Context and Human Validation after investigation', () => {
    expect(agentInvestigation).toContain('id="candidate-agent-investigation"')
    expect(detailPage).toContain('CandidateAgentInvestigation')
    expect(agentInvestigation).toContain('Agent Investigation')
    expect(humanValidation).toContain('id="candidate-human-validation"')
    expect(detailPage).toContain('CandidateHumanValidation')
    expect(humanValidation).toContain('Human Validation')

    const evidenceStart = detailPage.indexOf('id="candidate-evidence-context"')
    const investigationStart = detailPage.indexOf('CandidateAgentInvestigation')
    const validationStart = detailPage.indexOf('CandidateHumanValidation')
    expect(investigationStart).toBeGreaterThan(evidenceStart)
    expect(validationStart).toBeGreaterThan(investigationStart)

    expect(detailPage).not.toContain('candidate-history')
    expect(candidateDetailSources).not.toMatch(/coming soon/i)
    expect(candidateDetailSources).not.toMatch(/agent analysis/i)
    expect(candidateDetailSources).not.toMatch(/audit event/i)
  })

  it('keeps Candidate Detail on the real Candidate API without a mock fallback', () => {
    expect(detailPage).toContain('useCandidateApi()')
    expect(detailPage).toContain('getCandidate')
    expect(detailPage).not.toContain('getMockCandidateDetail')
    expect(detailPage).not.toContain('getCandidates')
  })
})
