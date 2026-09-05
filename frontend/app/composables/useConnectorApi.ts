import { $fetch } from 'ofetch'
import type { ConnectorApiListResponse } from '../types/connectorApi'

const CONNECTORS_PATH = '/api/v1/connectors'

export class ConnectorApiConfigurationError extends Error {
  constructor() {
    super('Public API base URL is not configured')
    this.name = 'ConnectorApiConfigurationError'
  }
}

export type ConnectorApiRequester = <T>(url: string) => Promise<T>

export interface ConnectorApi {
  getConnectors: () => Promise<ConnectorApiListResponse>
}

export function createConnectorApi(options: {
  apiBaseUrl: string
  request: ConnectorApiRequester
}): ConnectorApi {
  async function getConnectors(): Promise<ConnectorApiListResponse> {
    return options.request<ConnectorApiListResponse>(
      resolveConnectorApiUrl(options.apiBaseUrl, CONNECTORS_PATH),
    )
  }

  return { getConnectors }
}

export function useConnectorApi(): ConnectorApi {
  const config = useRuntimeConfig()
  return createConnectorApi({
    apiBaseUrl: config.public.apiBaseUrl,
    request: (url) => $fetch(url),
  })
}

function resolveConnectorApiUrl(apiBaseUrl: string, resourcePath: string): string {
  const trimmedBaseUrl = apiBaseUrl.trim()
  if (!trimmedBaseUrl) {
    throw new ConnectorApiConfigurationError()
  }

  const origin = trimmedBaseUrl.replace(/\/+$/, '')
  const path = resourcePath.startsWith('/') ? resourcePath : `/${resourcePath}`
  return `${origin}${path}`
}
