import { describe, expect, it, vi } from 'vitest'
import {
  ConnectorApiConfigurationError,
  createConnectorApi,
} from '../../app/composables/useConnectorApi'
import type { ConnectorApiListResponse } from '../../app/types/connectorApi'

const API_ORIGIN = 'https://connector-api.example.test'

const listPayload: ConnectorApiListResponse = {
  items: [
    {
      connector_id: 'dependency-lifecycle',
      display_name: 'Dependency Lifecycle',
      version: '1.0.0',
      source_system: 'dependency-lifecycle',
      transport: 'local-json',
      read_only: true,
      status: 'registered',
    },
    {
      connector_id: 'github-issues',
      display_name: 'GitHub Issues',
      version: '1.0.0',
      source_system: 'github-issues',
      transport: 'https',
      read_only: true,
      status: 'registered',
    },
  ],
  count: 2,
}

function httpError(statusCode: number, detail: string) {
  const error = new Error(detail) as Error & {
    statusCode: number
    data: { detail: string }
  }
  error.statusCode = statusCode
  error.data = { detail }
  return error
}

describe('createConnectorApi', () => {
  it('calls GET /api/v1/connectors with the configured API base URL', async () => {
    const request = vi.fn().mockResolvedValue(listPayload)
    const api = createConnectorApi({ apiBaseUrl: API_ORIGIN, request })

    const result = await api.getConnectors()

    expect(request).toHaveBeenCalledWith(`${API_ORIGIN}/api/v1/connectors`)
    expect(result).toBe(listPayload)
  })

  it('does not introduce a duplicate slash when the API base URL has a trailing slash', async () => {
    const request = vi.fn().mockResolvedValue(listPayload)
    const api = createConnectorApi({ apiBaseUrl: `${API_ORIGIN}/`, request })

    await api.getConnectors()

    expect(request).toHaveBeenCalledWith(`${API_ORIGIN}/api/v1/connectors`)
  })

  it('returns the wire JSON without presentation mapping or health fields', async () => {
    const request = vi.fn().mockResolvedValue(listPayload)
    const api = createConnectorApi({ apiBaseUrl: API_ORIGIN, request })

    const result = await api.getConnectors()
    const item = result.items[0]

    expect(item).toEqual(listPayload.items[0])
    expect(item).toHaveProperty('connector_id', 'dependency-lifecycle')
    expect(item).toHaveProperty('read_only', true)
    expect(item).toHaveProperty('status', 'registered')
    expect(item).not.toHaveProperty('connectorId')
    expect(item).not.toHaveProperty('displayName')
    expect(item).not.toHaveProperty('health')
    expect(item).not.toHaveProperty('last_run')
    expect(item).not.toHaveProperty('enabled')
  })

  it('fails before requesting when the public API base URL is missing', async () => {
    const request = vi.fn()
    const api = createConnectorApi({ apiBaseUrl: '', request })

    await expect(api.getConnectors()).rejects.toBeInstanceOf(ConnectorApiConfigurationError)
    await expect(api.getConnectors()).rejects.toThrow('Public API base URL is not configured')
    expect(request).not.toHaveBeenCalled()
  })

  it('fails before requesting when the public API base URL is blank', async () => {
    const request = vi.fn()
    const api = createConnectorApi({ apiBaseUrl: '   ', request })

    await expect(api.getConnectors()).rejects.toThrow('Public API base URL is not configured')
    expect(request).not.toHaveBeenCalled()
  })

  it('does not convert HTTP failures into a successful empty connector list', async () => {
    const failure = httpError(500, 'Internal Server Error')
    const request = vi.fn().mockRejectedValue(failure)

    await expect(
      createConnectorApi({ apiBaseUrl: API_ORIGIN, request }).getConnectors(),
    ).rejects.toMatchObject({ statusCode: 500, data: { detail: failure.data.detail } })
  })

  it('does not call GitHub or embed a hard-coded connector inventory', async () => {
    const request = vi.fn().mockResolvedValue(listPayload)
    const api = createConnectorApi({ apiBaseUrl: API_ORIGIN, request })

    await api.getConnectors()

    expect(request).toHaveBeenCalledTimes(1)
    expect(request.mock.calls[0]?.[0]).not.toContain('api.github.com')
    expect(request.mock.calls[0]?.[0]).toBe(`${API_ORIGIN}/api/v1/connectors`)
  })
})
