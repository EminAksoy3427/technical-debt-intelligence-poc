import { describe, expect, it } from 'vitest'
import { resolveConnectorInventoryViewState } from '../../app/utils/resolveConnectorInventoryViewState'

describe('resolveConnectorInventoryViewState', () => {
  it('returns loading while the list request is in progress', () => {
    expect(
      resolveConnectorInventoryViewState({
        pending: true,
        hasError: false,
        hasListResponse: false,
        connectorCount: 0,
      }),
    ).toBe('loading')
  })

  it('returns loading until a successful list response is present', () => {
    expect(
      resolveConnectorInventoryViewState({
        pending: false,
        hasError: false,
        hasListResponse: false,
        connectorCount: 0,
      }),
    ).toBe('loading')
  })

  it('does not treat an API failure as a successful empty inventory', () => {
    expect(
      resolveConnectorInventoryViewState({
        pending: false,
        hasError: true,
        hasListResponse: false,
        connectorCount: 0,
      }),
    ).toBe('error')
  })

  it('returns empty when the backend successfully returns zero connectors', () => {
    expect(
      resolveConnectorInventoryViewState({
        pending: false,
        hasError: false,
        hasListResponse: true,
        connectorCount: 0,
      }),
    ).toBe('empty')
  })

  it('returns ready when registered connectors are available', () => {
    expect(
      resolveConnectorInventoryViewState({
        pending: false,
        hasError: false,
        hasListResponse: true,
        connectorCount: 2,
      }),
    ).toBe('ready')
  })
})
