import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const testsDirectory = dirname(fileURLToPath(import.meta.url))
const frontendAppDirectory = join(testsDirectory, '../../app')

function readFrontendSource(relativePath: string): string {
  return readFileSync(join(frontendAppDirectory, relativePath), 'utf8')
}

function headingAndLabelText(source: string): string {
  const headings = [...source.matchAll(/<h[1-6][^>]*>\s*([^<]+)/g)].map((match) => match[1].trim())
  const labels = [...source.matchAll(/<dt>\s*([^<]+)/g)].map((match) => match[1].trim())
  return [...headings, ...labels].join('\n')
}

const detailPage = readFrontendSource('pages/candidates/[id].vue')
const header = readFrontendSource('components/candidate/CandidateDetailHeader.vue')
const display = readFrontendSource('utils/candidateDetailDisplay.ts')
const enterpriseContext = readFrontendSource(
  'components/candidate/CandidateEnterpriseContext.vue',
)
const dependencyContext = readFrontendSource(
  'components/candidate/CandidateDependencyContext.vue',
)
const dependencyAssetList = readFrontendSource(
  'components/candidate/CandidateDependencyAssetList.vue',
)
const mapper = readFrontendSource('utils/mapCandidateDetail.ts')
const agentInvestigation = readFrontendSource(
  'components/candidate/CandidateAgentInvestigation.vue',
)
const structuredAssessment = readFrontendSource(
  'components/candidate/CandidateStructuredAssessment.vue',
)
const policyTrace = readFrontendSource(
  'components/candidate/CandidateAgentPolicyTrace.vue',
)
const humanValidation = readFrontendSource(
  'components/candidate/CandidateHumanValidation.vue',
)

const misleadingLabels = [
  'TechnicalDebt owner',
  'Candidate owner',
  'Suggested Team',
  'Recommended owner',
  'Assigned team',
  'Risk score',
  'Impact score',
  'Caused by',
  'Caused incident',
  'Blast radius',
  'Impacted systems',
  'Expected outage',
  'Systems at risk',
  'Affected downstream systems',
]

describe('Candidate Detail D2 semantic copy', () => {
  it('does not label ownership, risk, causality, or impact with misleading phrases', () => {
    const labels = [
      headingAndLabelText(detailPage),
      headingAndLabelText(header),
      headingAndLabelText(enterpriseContext),
      headingAndLabelText(dependencyContext),
      headingAndLabelText(agentInvestigation),
      headingAndLabelText(structuredAssessment),
      headingAndLabelText(policyTrace),
      headingAndLabelText(humanValidation),
    ].join('\n')

    for (const phrase of misleadingLabels) {
      expect(labels).not.toContain(phrase)
    }
  })

  it('labels criticality as asset criticality and lifecycle as asset lifecycle', () => {
    expect(header).toContain('Asset criticality')
    expect(header).toContain('Asset lifecycle status')
    expect(header).toContain('candidateAssetCriticalityLabels[asset.criticality]')
    expect(header).toContain('candidateAssetLifecycleStatusLabels[asset.lifecycleStatus]')
    expect(header).toContain('candidateGovernanceDistinctionNotice')
    expect(display).toContain('Not TechnicalDebt.')
    expect(display).toContain('Candidate awaiting human validation.')
    expect(headingAndLabelText(header)).not.toContain('Candidate risk')
    expect(headingAndLabelText(header)).not.toContain('Technical debt risk')
    expect(headingAndLabelText(detailPage)).not.toContain('Candidate risk')
  })

  it('labels ownership as enterprise asset ownership', () => {
    expect(enterpriseContext).toContain('Enterprise asset ownership')
    expect(enterpriseContext).toContain(
      'These records describe ownership of the enterprise asset, not validated TechnicalDebt ownership.',
    )
    expect(enterpriseContext).toContain('None recorded.')
  })

  it('presents relationships as recorded structure without causality claims', () => {
    expect(enterpriseContext).toContain('Direct relationships')
    expect(enterpriseContext).toContain(
      'Relationships describe recorded enterprise structure; they do not establish Candidate causality.',
    )
    expect(enterpriseContext).toContain('None recorded.')
    expect(enterpriseContext).not.toContain('will fail')
  })

  it('presents incidents as associated context and keeps incident severity distinct', () => {
    expect(enterpriseContext).toContain('Direct incidents')
    expect(enterpriseContext).toContain('Incident severity')
    expect(enterpriseContext).toContain(
      'Incidents are associated operational context and do not prove that this Candidate caused them.',
    )
    expect(enterpriseContext).toContain('None recorded.')
    expect(enterpriseContext).not.toContain('active outage')
    expect(enterpriseContext).not.toContain('Still ongoing')
  })

  it('labels reachable dependents as reachability, not impact', () => {
    expect(dependencyContext).toContain('Dependency anchors')
    expect(dependencyContext).toContain('Direct dependencies')
    expect(dependencyContext).toContain('Direct dependents')
    expect(dependencyContext).toContain('Reachable dependents')
    expect(dependencyContext).toContain(
      'Reachability represents graph connectivity and does not imply guaranteed operational impact or outage.',
    )
    expect(dependencyAssetList).toContain('None recorded.')
    expect(headingAndLabelText(dependencyContext)).not.toContain('Impacted systems')
    expect(headingAndLabelText(dependencyContext)).not.toContain('Blast radius')
  })

  it('keeps Human Validation copy distinct from approval, risk, and ownership', () => {
    expect(humanValidation).toContain('HUMAN_VALIDATION_DISTINCTION')
    expect(humanValidation).toContain('Audit actor')
    expect(humanValidation).toContain('Open TechnicalDebt record')
    expect(headingAndLabelText(humanValidation)).not.toContain('Approve')
    expect(headingAndLabelText(humanValidation)).not.toContain('Risk score')
    expect(headingAndLabelText(humanValidation)).not.toContain('TechnicalDebt owner')
  })

  it('keeps Agent Investigation copy distinct from validation, approval, and risk', () => {
    expect(agentInvestigation).toContain('does not validate the')
    expect(agentInvestigation).toContain('This is not Candidate validation.')
    expect(agentInvestigation).toContain('This is not')
    expect(agentInvestigation).toContain('Candidate rejection.')
    expect(policyTrace).toContain('Policy ALLOW is not human approval.')
    expect(headingAndLabelText(agentInvestigation)).not.toContain('Candidate risk')
    expect(headingAndLabelText(structuredAssessment)).not.toContain('Risk score')
    expect(headingAndLabelText(policyTrace)).not.toContain('Human Approved')
  })

  it('does not compute graph reachability in the frontend mapper', () => {
    expect(mapper).not.toMatch(/\bancestors\b/)
    expect(mapper).not.toMatch(/\bsuccessors\b/)
    expect(mapper).not.toMatch(/\bpredecessors\b/)
    expect(mapper).not.toContain('networkx')
    expect(mapper).not.toContain('DiGraph')
    expect(mapper).not.toContain('blastRadius')
    expect(mapper).not.toContain('impactScore')
  })
})
