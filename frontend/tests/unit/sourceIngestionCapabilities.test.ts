import { describe, expect, it } from 'vitest'
import { implementedSignalSources } from '../../app/utils/implementedSignalSources'
import { sourceIngestionCapabilities } from '../../app/utils/sourceIngestionCapabilities'
import { sourceIngestionPipelineStages } from '../../app/utils/sourceIngestionPipeline'

describe('source ingestion capabilities', () => {
  it('lists only verified Signal-producing sources', () => {
    expect(sourceIngestionCapabilities.map((source) => source.id)).toEqual(
      implementedSignalSources.map((source) => source.id),
    )
    expect(sourceIngestionCapabilities.map((source) => source.id)).toEqual([
      'semgrep',
      'git',
      'incident-management',
      'dependency-lifecycle',
    ])
    expect(sourceIngestionCapabilities.map((source) => source.name)).toEqual([
      'Semgrep',
      'Git SATD',
      'Incident management',
      'Dependency lifecycle',
    ])
    expect(
      sourceIngestionCapabilities.every(
        (source) => source.normalizedRole === 'NormalizedSignal + Evidence',
      ),
    ).toBe(true)
  })

  it('does not present GitHub Issues or speculative systems as Signal sources', () => {
    const serialized = JSON.stringify(sourceIngestionCapabilities)

    expect(serialized).not.toContain('github-issues')
    expect(serialized).not.toContain('GitHub')
    expect(serialized).not.toContain('Kafka')
    expect(serialized).not.toContain('Jira')
    expect(serialized).not.toContain('SonarQube')
    expect(serialized).not.toContain('Bitbucket')
    expect(serialized).not.toContain('Healthy')
    expect(serialized).not.toContain('Connected')
    expect(serialized).not.toContain('Last synced')
  })
})

describe('source ingestion pipeline', () => {
  it('normalizes before Candidate and keeps Candidate distinct from TechnicalDebt', () => {
    const names = sourceIngestionPipelineStages.map((stage) => stage.name)

    expect(names.indexOf('Normalizer')).toBeLessThan(
      names.indexOf('NormalizedSignal + Evidence'),
    )
    expect(names.indexOf('NormalizedSignal + Evidence')).toBeLessThan(
      names.indexOf('Correlation'),
    )
    expect(names.indexOf('Correlation')).toBeLessThan(names.indexOf('Candidate'))
    expect(names.at(-1)).toBe('Candidate')
    expect(names).not.toContain('TechnicalDebt')
    expect(
      sourceIngestionPipelineStages.find((stage) => stage.id === 'candidate')
        ?.description,
    ).toContain('A Candidate is not TechnicalDebt')
    expect(names).toContain('SourceObservation')
  })
})
