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
    expect(detailPage).not.toContain('CandidateContext')
    expect(detailPage).not.toMatch(/CND-/)
    expect(detailPage).not.toContain('data_store')
  })

  it('keeps Pool UUID navigation compatible with the Detail route', () => {
    expect(poolTable).toContain('`/candidates/${candidate.id}`')
    expect(poolTable).not.toMatch(/CND-/)
  })
})
