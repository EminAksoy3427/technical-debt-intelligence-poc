import {
  connectorAccessLabel,
  connectorTransportLabel,
  type ConnectorSummary,
} from '../types/connector'

/**
 * Capability notes verified from connector implementations, not from the API.
 * GET /api/v1/connectors returns registration metadata only.
 *
 * github-issues: backend/app/connectors/github_issues.py
 *   acquire → SourceObservation; no normalizer; does not produce Signals
 * dependency-lifecycle: backend/app/connectors/dependency_lifecycle.py
 *   acquire → SourceObservation; separate normalize_dependency_lifecycle_observation
 *
 * Unknown registered connectors are shown as inventory only.
 * Do not infer health, connectivity, or Signal production from a name.
 */
export type ConnectorCapabilityKind =
  | 'acquisition-only'
  | 'acquisition-and-normalization'
  | 'registered'

export interface AnnotatedConnector extends ConnectorSummary {
  capabilityKind: ConnectorCapabilityKind
  roleLabel: string
  capabilitySummary: string | null
}

export interface ConnectorTechnicalDetailRow {
  label: string
  value: string
}

const knownConnectorCapabilities: Record<
  string,
  Pick<AnnotatedConnector, 'capabilityKind' | 'roleLabel' | 'capabilitySummary'>
> = {
  'github-issues': {
    capabilityKind: 'acquisition-only',
    roleLabel: 'Acquisition connector',
    capabilitySummary:
      'Retrieves source records as SourceObservation for controlled acquisition. Does not currently normalize observations into technical-debt Signals.',
  },
  'dependency-lifecycle': {
    capabilityKind: 'acquisition-and-normalization',
    roleLabel: 'Acquisition and normalization',
    capabilitySummary:
      'Acquires lifecycle findings as SourceObservation. A separate normalizer maps them into NormalizedSignal and Evidence.',
  },
}

export function annotateRegisteredConnector(
  connector: ConnectorSummary,
): AnnotatedConnector {
  const known = knownConnectorCapabilities[connector.connectorId]
  if (known != null) {
    return {
      ...connector,
      ...known,
    }
  }

  return {
    ...connector,
    capabilityKind: 'registered',
    roleLabel: 'Registered connector',
    capabilitySummary: null,
  }
}

export function connectorTechnicalDetailRows(
  connector: ConnectorSummary,
): ConnectorTechnicalDetailRow[] {
  return [
    { label: 'Connector key', value: connector.connectorId },
    { label: 'Source system', value: connector.sourceSystem },
    { label: 'Transport', value: connectorTransportLabel(connector.transport) },
    { label: 'Access', value: connectorAccessLabel(connector.readOnly) },
    { label: 'Version', value: connector.version },
  ]
}

export function isAcquisitionOnlyConnector(connector: AnnotatedConnector): boolean {
  return connector.capabilityKind === 'acquisition-only'
}
