import { describe, expect, it } from 'vitest'
import { implementedSignalSources } from '../../app/utils/implementedSignalSources'

describe('implementedSignalSources', () => {
  it('lists only verified ingestion capabilities', () => {
    expect(implementedSignalSources.map((source) => source.id)).toEqual([
      'semgrep',
      'git',
      'incident-management',
      'dependency-lifecycle',
    ])
    expect(implementedSignalSources.map((source) => source.name)).toEqual([
      'Semgrep',
      'Git',
      'Incident management',
      'Dependency lifecycle',
    ])
  })

  it('does not present GitHub Issues or unverified systems as signal sources', () => {
    const serialized = JSON.stringify(implementedSignalSources)

    expect(serialized).not.toContain('github-issues')
    expect(serialized).not.toContain('GitHub')
    expect(serialized).not.toContain('Kafka')
    expect(serialized).not.toContain('Jira')
    expect(serialized).not.toContain('SonarQube')
    expect(serialized).not.toContain('Healthy')
    expect(serialized).not.toContain('Connected')
    expect(serialized).not.toContain('Last synced')
    expect(serialized).not.toContain('Live')
  })
})
