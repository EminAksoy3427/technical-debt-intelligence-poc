import { httpStatusFromUnknownError } from './resolveCandidateDetailViewState'

export type GovernedMutationStatus =
  | 'success'
  | 'success-refresh-failed'
  | 'conflict'
  | 'reconciliation-unresolved'
  | 'forbidden'
  | 'error'

export async function submitGovernedMutation<T>(input: {
  mutate: () => Promise<T>
  refreshTechnicalDebt: () => Promise<unknown>
  recognizeReconciliationConflict?: boolean
}): Promise<{ status: GovernedMutationStatus; resource: T | null }> {
  let resource: T
  try {
    resource = await input.mutate()
  } catch (error) {
    const status = httpStatusFromUnknownError(error)
    if (status === 409) {
      try {
        await input.refreshTechnicalDebt()
      } catch {
        // Never repeat the mutation when the conflict refresh fails.
      }
      return {
        status:
          input.recognizeReconciliationConflict && errorDetail(error).includes('reconcil')
            ? 'reconciliation-unresolved'
            : 'conflict',
        resource: null,
      }
    }
    return { status: status === 403 ? 'forbidden' : 'error', resource: null }
  }

  try {
    await input.refreshTechnicalDebt()
    return { status: 'success', resource }
  } catch {
    return { status: 'success-refresh-failed', resource }
  }
}

function errorDetail(error: unknown): string {
  if (typeof error !== 'object' || error == null || !('data' in error)) {
    return ''
  }
  const data = (error as { data?: { detail?: unknown } }).data
  return typeof data?.detail === 'string' ? data.detail.toLowerCase() : ''
}
