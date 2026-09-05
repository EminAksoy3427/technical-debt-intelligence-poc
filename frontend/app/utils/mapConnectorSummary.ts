import type { ConnectorSummary } from '../types/connector'
import type { ConnectorApiItem } from '../types/connectorApi'

export function toConnectorSummary(item: ConnectorApiItem): ConnectorSummary {
  return {
    connectorId: item.connector_id,
    displayName: item.display_name,
    version: item.version,
    sourceSystem: item.source_system,
    transport: item.transport,
    readOnly: item.read_only,
    status: item.status,
  }
}
