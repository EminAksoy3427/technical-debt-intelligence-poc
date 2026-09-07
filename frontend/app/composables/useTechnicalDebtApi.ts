import { $fetch } from 'ofetch'
import type {
  ActionApproval,
  ActionExecution,
  ActionProposal,
  ActionVerification,
  ApproveActionProposalRequest,
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
  body?: ApproveActionProposalRequest
}

export type TechnicalDebtApiRequester = <T>(
  url: string,
  options?: TechnicalDebtApiRequestOptions,
) => Promise<T>

export interface TechnicalDebtApi {
  listTechnicalDebts: () => Promise<TechnicalDebtListResponse>
  getTechnicalDebt: (technicalDebtId: string) => Promise<TechnicalDebtDetail>
  prepareActionProposal: (technicalDebtId: string) => Promise<ActionProposal>
  approveActionProposal: (
    technicalDebtId: string,
    actionProposalId: string,
    request: ApproveActionProposalRequest,
  ) => Promise<ActionApproval>
  executeActionProposal: (
    technicalDebtId: string,
    actionProposalId: string,
  ) => Promise<ActionExecution>
  verifyActionExecution: (
    technicalDebtId: string,
    actionProposalId: string,
    actionExecutionId: string,
  ) => Promise<ActionVerification>
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

  async function approveActionProposal(
    technicalDebtId: string,
    actionProposalId: string,
    request: ApproveActionProposalRequest,
  ): Promise<ActionApproval> {
    return options.request<ActionApproval>(
      resolveTechnicalDebtApiUrl(
        options.apiBaseUrl,
        `${TECHNICAL_DEBTS_PATH}/${encodeURIComponent(technicalDebtId)}/action-proposals/${encodeURIComponent(actionProposalId)}/approvals`,
      ),
      { method: 'POST', body: request },
    )
  }

  async function executeActionProposal(
    technicalDebtId: string,
    actionProposalId: string,
  ): Promise<ActionExecution> {
    return options.request<ActionExecution>(
      resolveTechnicalDebtApiUrl(
        options.apiBaseUrl,
        `${TECHNICAL_DEBTS_PATH}/${encodeURIComponent(technicalDebtId)}/action-proposals/${encodeURIComponent(actionProposalId)}/executions`,
      ),
      { method: 'POST' },
    )
  }

  async function verifyActionExecution(
    technicalDebtId: string,
    actionProposalId: string,
    actionExecutionId: string,
  ): Promise<ActionVerification> {
    return options.request<ActionVerification>(
      resolveTechnicalDebtApiUrl(
        options.apiBaseUrl,
        `${TECHNICAL_DEBTS_PATH}/${encodeURIComponent(technicalDebtId)}/action-proposals/${encodeURIComponent(actionProposalId)}/executions/${encodeURIComponent(actionExecutionId)}/verifications`,
      ),
      { method: 'POST' },
    )
  }

  return {
    listTechnicalDebts,
    getTechnicalDebt,
    prepareActionProposal,
    approveActionProposal,
    executeActionProposal,
    verifyActionExecution,
  }
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
