/**
 * FastAPI Connector Registry API wire DTOs.
 * These types describe JSON from GET /api/v1/connectors.
 * They are inventory metadata, not source health and not TechnicalDebt.
 */

export type ConnectorApiStatus = 'registered'

export interface ConnectorApiItem {
  connector_id: string
  display_name: string
  version: string
  source_system: string
  transport: string
  read_only: boolean
  status: ConnectorApiStatus
}

export interface ConnectorApiListResponse {
  items: ConnectorApiItem[]
  count: number
}
