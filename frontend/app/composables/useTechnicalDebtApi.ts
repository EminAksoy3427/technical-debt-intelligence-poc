import { $fetch } from 'ofetch'
import type {
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

export type TechnicalDebtApiRequester = <T>(url: string) => Promise<T>

export interface TechnicalDebtApi {
  listTechnicalDebts: () => Promise<TechnicalDebtListResponse>
  getTechnicalDebt: (technicalDebtId: string) => Promise<TechnicalDebtDetail>
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

  return { listTechnicalDebts, getTechnicalDebt }
}

export function useTechnicalDebtApi(): TechnicalDebtApi {
  const config = useRuntimeConfig()
  return createTechnicalDebtApi({
    apiBaseUrl: config.public.apiBaseUrl,
    request: (url) => $fetch(url),
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
