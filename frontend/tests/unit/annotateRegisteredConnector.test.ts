import { describe, expect, it } from 'vitest'
import type { ConnectorSummary } from '../../app/types/connector'
import {
  annotateRegisteredConnector,
  connectorTechnicalDetailRows,
  isAcquisitionOnlyConnector,
} from '../../app/utils/annotateRegisteredConnector'

const githubIssues: ConnectorSummary = {
  connectorId: 'github-issues',
  displayName: 'GitHub Issues',
  version: '1.0.0',
  sourceSystem: 'github-issues',
  transport: 'https',
  readOnly: true,
  status: 'registered',
}

const dependencyLifecycle: ConnectorSummary = {
  connectorId: 'dependency-lifecycle',
  displayName: 'Dependency Lifecycle',
  version: '1.0.0',
  sourceSystem: 'dependency-lifecycle',
  transport: 'local-json',
  readOnly: true,
  status: 'registered',
}

const unknownConnector: ConnectorSummary = {
  connectorId: 'future-source',
  displayName: 'Future Source',
  version: '0.0.1',
  sourceSystem: 'future-source',
  transport: 'https',
  readOnly: true,
  status: 'registered',
}

describe('annotateRegisteredConnector', () => {
  it('marks GitHub Issues as acquisition-only and not Signal-producing', () => {
    const annotated = annotateRegisteredConnector(githubIssues)

    expect(annotated.capabilityKind).toBe('acquisition-only')
    expect(annotated.roleLabel).toBe('Acquisition connector')
    expect(annotated.capabilitySummary).toContain('SourceObservation')
    expect(annotated.capabilitySummary).toContain(
      'Does not currently normalize observations into technical-debt Signals',
    )
    expect(isAcquisitionOnlyConnector(annotated)).toBe(true)
    expect(annotated.status).toBe('registered')
  })

  it('marks Dependency Lifecycle as acquisition with a separate normalizer', () => {
    const annotated = annotateRegisteredConnector(dependencyLifecycle)

    expect(annotated.capabilityKind).toBe('acquisition-and-normalization')
    expect(annotated.roleLabel).toBe('Acquisition and normalization')
    expect(annotated.capabilitySummary).toContain('SourceObservation')
    expect(annotated.capabilitySummary).toContain('NormalizedSignal')
    expect(isAcquisitionOnlyConnector(annotated)).toBe(false)
  })

  it('does not invent capability semantics for unknown registered connectors', () => {
    const annotated = annotateRegisteredConnector(unknownConnector)

    expect(annotated.capabilityKind).toBe('registered')
    expect(annotated.roleLabel).toBe('Registered connector')
    expect(annotated.capabilitySummary).toBeNull()
    expect(annotated.status).toBe('registered')
  })

  it('exposes technical identifiers only as disclosure rows from API fields', () => {
    expect(connectorTechnicalDetailRows(githubIssues)).toEqual([
      { label: 'Connector key', value: 'github-issues' },
      { label: 'Source system', value: 'github-issues' },
      { label: 'Transport', value: 'HTTPS' },
      { label: 'Access', value: 'Read only' },
      { label: 'Version', value: '1.0.0' },
    ])
  })
})
