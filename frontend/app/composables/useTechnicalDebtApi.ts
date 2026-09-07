import { $fetch } from 'ofetch'
import type {
  ActionProposal,
  TechnicalDebtDetail,
  TechnicalDebtListResponse,
} from '../types/technicalDebtApi'

const TECHNICAL_DEBTS_PATH = '/api/v1/technical-debts'

export class TechnicalDebtApiConfigurationError extends Error {
  constructor() {
    super('Public API base URL is not configured')
    this.name = 'TechnicalDebtApiConfigurationError'
  }
}

export interface TechnicalDebtApiRequestOptions {
  method?: 'GET' | 'POST'
}

export type TechnicalDebtApiRequester = <T>(
  url: string,
  options?: TechnicalDebtApiRequestOptions,
) => Promise<T>

export interface TechnicalDebtApi {
  listTechnicalDebts: () => Promise<TechnicalDebtListResponse>
  getTechnicalDebt: (technicalDebtId: string) => Promise<TechnicalDebtDetail>
  prepareActionProposal: (technicalDebtId: string) => Promise<ActionProposal>
}

export function createTechnicalDebtApi(options: {
  apiBaseUrl: string
  request: TechnicalDebtApiRequester
}): TechnicalDebtApi {
  async function listTechnicalDebts(): Promise<TechnicalDebtListResponse> {
    return options.request<TechnicalDebtListResponse>(
      resolveTechnicalDebtApiUrl(options.apiBaseUrl, TECHNICAL_DEBTS_PATH),
    )
  }

  async function getTechnicalDebt(technicalDebtId: string): Promise<TechnicalDebtDetail> {
    return options.request<TechnicalDebtDetail>(
      resolveTechnicalDebtApiUrl(
        options.apiBaseUrl,
        `${TECHNICAL_DEBTS_PATH}/${encodeURIComponent(technicalDebtId)}`,
      ),
    )
  }

  async function prepareActionProposal(technicalDebtId: string): Promise<ActionProposal> {
    return options.request<ActionProposal>(
      resolveTechnicalDebtApiUrl(
        options.apiBaseUrl,
        `${TECHNICAL_DEBTS_PATH}/${encodeURIComponent(technicalDebtId)}/action-proposals`,
      ),
      { method: 'POST' },
    )
  }

  return { listTechnicalDebts, getTechnicalDebt, prepareActionProposal }
}

export function useTechnicalDebtApi(): TechnicalDebtApi {
  const config = useRuntimeConfig()
  return createTechnicalDebtApi({
    apiBaseUrl: config.public.apiBaseUrl,
    request: (url, requestOptions) => $fetch(url, requestOptions),
  })
}

function resolveTechnicalDebtApiUrl(apiBaseUrl: string, resourcePath: string): string {
  const trimmedBaseUrl = apiBaseUrl.trim()
  if (!trimmedBaseUrl) {
    throw new TechnicalDebtApiConfigurationError()
  }

  const origin = trimmedBaseUrl.replace(/\/+$/, '')
  const path = resourcePath.startsWith('/') ? resourcePath : `/${resourcePath}`
  return `${origin}${path}`
}
