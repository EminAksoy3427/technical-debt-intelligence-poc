import { describe, expect, it } from 'vitest'
import type { ConnectorApiItem } from '../../app/types/connectorApi'
import {
  connectorAccessLabel,
  connectorStatusLabel,
  connectorTransportLabel,
} from '../../app/types/connector'
import { toConnectorSummary } from '../../app/utils/mapConnectorSummary'

const dependencyLifecycleItem: ConnectorApiItem = {
  connector_id: 'dependency-lifecycle',
  display_name: 'Dependency Lifecycle',
  version: '1.0.0',
  source_system: 'dependency-lifecycle',
  transport: 'local-json',
  read_only: true,
  status: 'registered',
}

const githubIssuesItem: ConnectorApiItem = {
  connector_id: 'github-issues',
  display_name: 'GitHub Issues',
  version: '1.0.0',
  source_system: 'github-issues',
  transport: 'https',
  read_only: true,
  status: 'registered',
}

describe('toConnectorSummary', () => {
  it('maps snake_case wire fields onto the camelCase presentation model', () => {
    expect(toConnectorSummary(dependencyLifecycleItem)).toEqual({
      connectorId: 'dependency-lifecycle',
      displayName: 'Dependency Lifecycle',
      version: '1.0.0',
      sourceSystem: 'dependency-lifecycle',
      transport: 'local-json',
      readOnly: true,
      status: 'registered',
    })
    expect(toConnectorSummary(githubIssuesItem)).toEqual({
      connectorId: 'github-issues',
      displayName: 'GitHub Issues',
      version: '1.0.0',
      sourceSystem: 'github-issues',
      transport: 'https',
      readOnly: true,
      status: 'registered',
    })
  })

  it('does not invent health, run history, or source payload fields', () => {
    const item = toConnectorSummary(dependencyLifecycleItem)

    expect(item).not.toHaveProperty('health')
    expect(item).not.toHaveProperty('lastRun')
    expect(item).not.toHaveProperty('lastError')
    expect(item).not.toHaveProperty('checkpoint')
    expect(item).not.toHaveProperty('enabled')
    expect(item).not.toHaveProperty('issueCount')
    expect(item).not.toHaveProperty('findingCount')
  })
})

describe('connector presentation labels', () => {
  it('maps known transports to Local JSON and HTTPS', () => {
    expect(connectorTransportLabel('local-json')).toBe('Local JSON')
    expect(connectorTransportLabel('https')).toBe('HTTPS')
  })

  it('maps registered status to Registered, not Healthy', () => {
    expect(connectorStatusLabel('registered')).toBe('Registered')
    expect(connectorStatusLabel('registered')).not.toBe('Healthy')
    expect(connectorStatusLabel('registered')).not.toBe('Connected')
    expect(connectorStatusLabel('registered')).not.toBe('Online')
    expect(connectorStatusLabel('registered')).not.toBe('Operational')
    expect(connectorStatusLabel('registered')).not.toBe('Live')
  })

  it('maps read-only access to Read only', () => {
    expect(connectorAccessLabel(true)).toBe('Read only')
  })
})
