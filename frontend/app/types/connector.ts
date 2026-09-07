/**
 * Frontend presentation model for the Sources connector inventory.
 * Mapped from ConnectorApiItem. Registration is composition inventory,
 * not source health, ingestion success, or TechnicalDebt.
 */
export interface ConnectorSummary {
  connectorId: string
  displayName: string
  version: string
  sourceSystem: string
  transport: string
  readOnly: boolean
  status: 'registered'
}

export const connectorTransportLabels = {
  'local-json': 'Local JSON',
  https: 'HTTPS',
} as const

export const connectorStatusLabels = {
  registered: 'Registered',
} as const

export function connectorTransportLabel(transport: string): string {
  if (transport === 'local-json') {
    return connectorTransportLabels['local-json']
  }
  if (transport === 'https') {
    return connectorTransportLabels.https
  }
  return transport
}

export function connectorAccessLabel(readOnly: boolean): string {
  return readOnly ? 'Read only' : 'Not read only'
}

export function connectorStatusLabel(status: ConnectorSummary['status']): string {
  return connectorStatusLabels[status]
}
