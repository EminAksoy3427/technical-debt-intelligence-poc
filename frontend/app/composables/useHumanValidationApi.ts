import { $fetch } from 'ofetch'
import type {
  HumanValidationRequest,
  HumanValidationResponse,
} from '../types/humanValidationApi'

const CANDIDATES_PATH = '/api/v1/candidates'

export class HumanValidationApiConfigurationError extends Error {
  constructor() {
    super('Public API base URL is not configured')
    this.name = 'HumanValidationApiConfigurationError'
  }
}

export interface HumanValidationApiRequestOptions {
  method: 'POST'
  body: HumanValidationRequest
}

export type HumanValidationApiRequester = <T>(
  url: string,
  options: HumanValidationApiRequestOptions,
) => Promise<T>

export interface HumanValidationApi {
  createHumanDecision: (
    candidateId: string,
    payload: HumanValidationRequest,
  ) => Promise<HumanValidationResponse>
}

export function createHumanValidationApi(options: {
  apiBaseUrl: string
  request: HumanValidationApiRequester
}): HumanValidationApi {
  async function createHumanDecision(
    candidateId: string,
    payload: HumanValidationRequest,
  ): Promise<HumanValidationResponse> {
    return options.request<HumanValidationResponse>(
      resolveHumanValidationApiUrl(
        options.apiBaseUrl,
        `${CANDIDATES_PATH}/${encodeURIComponent(candidateId)}/human-decisions`,
      ),
      { method: 'POST', body: payload },
    )
  }

  return { createHumanDecision }
}

export function useHumanValidationApi(): HumanValidationApi {
  const config = useRuntimeConfig()
  return createHumanValidationApi({
    apiBaseUrl: config.public.apiBaseUrl,
    request: (url, requestOptions) => $fetch(url, requestOptions),
  })
}

function resolveHumanValidationApiUrl(apiBaseUrl: string, resourcePath: string): string {
  const trimmedBaseUrl = apiBaseUrl.trim()
  if (!trimmedBaseUrl) {
    throw new HumanValidationApiConfigurationError()
  }

  const origin = trimmedBaseUrl.replace(/\/+$/, '')
  const path = resourcePath.startsWith('/') ? resourcePath : `/${resourcePath}`
  return `${origin}${path}`
}
