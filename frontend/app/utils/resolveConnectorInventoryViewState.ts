export type ConnectorInventoryViewState = 'loading' | 'error' | 'empty' | 'ready'

export function resolveConnectorInventoryViewState(input: {
  pending: boolean
  hasError: boolean
  hasListResponse: boolean
  connectorCount: number
}): ConnectorInventoryViewState {
  if (input.hasError) {
    return 'error'
  }

  if (input.pending || !input.hasListResponse) {
    return 'loading'
  }

  if (input.connectorCount === 0) {
    return 'empty'
  }

  return 'ready'
}
