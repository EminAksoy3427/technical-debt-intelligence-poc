import { $fetch } from 'ofetch'
import type { AgentRunResponse } from '../types/agentRunApi'

const CANDIDATES_PATH = '/api/v1/candidates'

export class AgentRunApiConfigurationError extends Error {
  constructor() {
    super('Public API base URL is not configured')
    this.name = 'AgentRunApiConfigurationError'
  }
}

export interface AgentRunApiRequestOptions {
  method?: 'GET' | 'POST'
}

export type AgentRunApiRequester = <T>(
  url: string,
  options?: AgentRunApiRequestOptions,
) => Promise<T>

export interface AgentRunApi {
  startCandidateInvestigation: (candidateId: string) => Promise<AgentRunResponse>
  getCandidateInvestigation: (
    candidateId: string,
    agentRunId: string,
  ) => Promise<AgentRunResponse>
}

export function createAgentRunApi(options: {
  apiBaseUrl: string
  request: AgentRunApiRequester
}): AgentRunApi {
  async function startCandidateInvestigation(
    candidateId: string,
  ): Promise<AgentRunResponse> {
    return options.request<AgentRunResponse>(
      resolveAgentRunApiUrl(
        options.apiBaseUrl,
        `${CANDIDATES_PATH}/${encodeURIComponent(candidateId)}/agent-runs`,
      ),
      { method: 'POST' },
    )
  }

  async function getCandidateInvestigation(
    candidateId: string,
    agentRunId: string,
  ): Promise<AgentRunResponse> {
    return options.request<AgentRunResponse>(
      resolveAgentRunApiUrl(
        options.apiBaseUrl,
        `${CANDIDATES_PATH}/${encodeURIComponent(candidateId)}/agent-runs/${encodeURIComponent(agentRunId)}`,
      ),
    )
  }

  return { startCandidateInvestigation, getCandidateInvestigation }
}

export function useAgentRunApi(): AgentRunApi {
  const config = useRuntimeConfig()
  return createAgentRunApi({
    apiBaseUrl: config.public.apiBaseUrl,
    request: (url, requestOptions) => $fetch(url, requestOptions),
  })
}

function resolveAgentRunApiUrl(apiBaseUrl: string, resourcePath: string): string {
  const trimmedBaseUrl = apiBaseUrl.trim()
  if (!trimmedBaseUrl) {
    throw new AgentRunApiConfigurationError()
  }

  const origin = trimmedBaseUrl.replace(/\/+$/, '')
  const path = resourcePath.startsWith('/') ? resourcePath : `/${resourcePath}`
  return `${origin}${path}`
}
