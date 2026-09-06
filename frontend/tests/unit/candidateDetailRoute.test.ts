import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const testsDirectory = dirname(fileURLToPath(import.meta.url))
const frontendAppDirectory = join(testsDirectory, '../../app')

function readFrontendSource(relativePath: string): string {
  return readFileSync(join(frontendAppDirectory, relativePath), 'utf8')
}

describe('Candidate Detail route source', () => {
  const detailPage = readFrontendSource('pages/candidates/[id].vue')
  const poolTable = readFrontendSource('components/candidate/CandidatePoolTable.vue')

  it('fetches Detail through useCandidateApi.getCandidate and the route Candidate ID', () => {
    expect(detailPage).toContain('useCandidateApi()')
    expect(detailPage).toContain('getCandidate')
    expect(detailPage).toContain('route.params.id')
    expect(detailPage).toContain('server: false')
    expect(detailPage).not.toContain('getMockCandidateDetail')
    expect(detailPage).not.toContain('$fetch(')
    expect(detailPage).not.toContain('axios')
  })

  it('does not keep mock Detail semantics on the runtime path', () => {
    expect(detailPage).not.toContain('reviewStatus')
    expect(detailPage).not.toContain('suggestedTeam')
    expect(detailPage).not.toContain('CandidateStatusBadge')
    expect(detailPage).not.toContain('<CandidateContext')
    expect(detailPage).not.toMatch(/CND-/)
    expect(detailPage).not.toContain('data_store')
  })

  it('reuses the D1 Detail response for enterprise and dependency context', () => {
    expect(detailPage).toContain('toCandidateDetailPresentation(data.value)')
    expect(detailPage).toContain('presentation.enterpriseContext')
    expect(detailPage).toContain('presentation.dependencyContext')
    expect(detailPage).not.toContain('getCandidates')
    expect(detailPage).not.toContain('/api/v1/assets')
    expect(detailPage).not.toContain('/api/v1/incidents')
    expect(detailPage).not.toContain('/api/v1/teams')
    expect(detailPage).not.toContain('/api/v1/dependencies')
    expect(detailPage).not.toContain('$fetch(')
  })

  it('keeps D1 Candidate, Signal, Evidence, and error-state rendering', () => {
    expect(detailPage).toContain('presentation.candidate.hypothesis')
    expect(detailPage).toContain('presentation.candidate.correlationRationale')
    expect(detailPage).toContain('CandidateSignalList')
    expect(detailPage).toContain('CandidateEvidenceList')
    expect(detailPage.indexOf('CandidateEvidenceList')).toBeLessThan(
      detailPage.indexOf('CandidateSignalList'),
    )
    expect(detailPage).toContain("viewState === 'loading'")
    expect(detailPage).toContain("viewState === 'not-found'")
    expect(detailPage).toContain("viewState === 'invalid-identifier'")
    expect(detailPage).toContain("viewState === 'error'")
    expect(detailPage).toContain('id="candidate-overview"')
    expect(detailPage).toContain('id="candidate-evidence-context"')
    expect(detailPage).toContain('CandidateAgentInvestigation')
    expect(detailPage).toContain('CandidateHumanValidation')
    expect(detailPage).toContain('refresh')
  })

  it('keeps Pool UUID navigation compatible with the Detail route', () => {
    expect(poolTable).toContain('`/candidates/${candidate.id}`')
    expect(poolTable).not.toMatch(/CND-/)
  })
})
