import { $fetch } from 'ofetch'
import type { CandidateDetailResponse, CandidateListResponse } from '../types/candidateApi'

const CANDIDATES_PATH = '/api/v1/candidates'

export class CandidateApiConfigurationError extends Error {
  constructor() {
    super('Public API base URL is not configured')
    this.name = 'CandidateApiConfigurationError'
  }
}

export type CandidateApiRequester = <T>(url: string) => Promise<T>

export interface CandidateApi {
  getCandidates: () => Promise<CandidateListResponse>
  getCandidate: (candidateId: string) => Promise<CandidateDetailResponse>
}

export function createCandidateApi(options: {
  apiBaseUrl: string
  request: CandidateApiRequester
}): CandidateApi {
  async function getCandidates(): Promise<CandidateListResponse> {
    return options.request<CandidateListResponse>(
      resolveCandidateApiUrl(options.apiBaseUrl, CANDIDATES_PATH),
    )
  }

  async function getCandidate(candidateId: string): Promise<CandidateDetailResponse> {
    return options.request<CandidateDetailResponse>(
      resolveCandidateApiUrl(
        options.apiBaseUrl,
        `${CANDIDATES_PATH}/${encodeURIComponent(candidateId)}`,
      ),
    )
  }

  return { getCandidates, getCandidate }
}

export function useCandidateApi(): CandidateApi {
  const config = useRuntimeConfig()
  return createCandidateApi({
    apiBaseUrl: config.public.apiBaseUrl,
    request: (url) => $fetch(url),
  })
}

function resolveCandidateApiUrl(apiBaseUrl: string, resourcePath: string): string {
  const trimmedBaseUrl = apiBaseUrl.trim()
  if (!trimmedBaseUrl) {
    throw new CandidateApiConfigurationError()
  }

  const origin = trimmedBaseUrl.replace(/\/+$/, '')
  const path = resourcePath.startsWith('/') ? resourcePath : `/${resourcePath}`
  return `${origin}${path}`
}
