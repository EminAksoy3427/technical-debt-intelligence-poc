<script setup lang="ts">
import type { CandidateEvidenceItem } from '~/types/candidate'
import type { AgentRunResponse } from '~/types/agentRunApi'
import { formatDisplayTimestamp } from '~/utils/candidateDetailDisplay'
import { toAgentInvestigationPresentation } from '~/utils/mapAgentRun'
import {
  resolveAgentInvestigationRequestError,
  resolveAgentInvestigationViewState,
  type AgentInvestigationRequestState,
} from '~/utils/resolveAgentInvestigationViewState'

const props = defineProps<{
  candidateId: string
  evidence: CandidateEvidenceItem[]
  isActive: boolean
}>()

const { startCandidateInvestigation } = useAgentRunApi()

const requestState = ref<AgentInvestigationRequestState>('idle')
const requestError = ref<unknown>(null)
const run = ref<AgentRunResponse | null>(null)

const isStarting = computed(() => requestState.value === 'starting')

const presentation = computed(() => {
  if (run.value == null) {
    return null
  }
  return toAgentInvestigationPresentation(run.value, props.evidence)
})

const viewState = computed(() =>
  resolveAgentInvestigationViewState({
    requestState: requestState.value,
    runStatus: run.value?.status ?? null,
  }),
)

const requestErrorMessage = computed(() => {
  if (requestState.value !== 'error') {
    return ''
  }
  return resolveAgentInvestigationRequestError({
    error: requestError.value,
    operation: 'start',
  })
})

const statusProvenanceRows = computed(() => {
  if (presentation.value == null) {
    return []
  }

  const rows = [
    { label: 'Investigation ID', value: presentation.value.agentRunId },
    { label: 'Status', value: presentation.value.status },
    { label: 'Created', value: formatDisplayTimestamp(presentation.value.createdAt) },
    { label: 'Created at (raw)', value: presentation.value.createdAt },
  ]
  if (presentation.value.startedAt != null) {
    rows.push(
      { label: 'Started', value: formatDisplayTimestamp(presentation.value.startedAt) },
      { label: 'Started at (raw)', value: presentation.value.startedAt },
    )
  }
  if (presentation.value.completedAt != null) {
    rows.push(
      { label: 'Completed', value: formatDisplayTimestamp(presentation.value.completedAt) },
      { label: 'Completed at (raw)', value: presentation.value.completedAt },
    )
  }
  if (presentation.value.stopReason != null) {
    rows.push({ label: 'Stop reason', value: presentation.value.stopReason })
  }
  return rows
})

function investigationStatusBadgeClass(status: string): string {
  if (status === 'FAILED') {
    return 'badge badge--danger'
  }
  if (status === 'ABSTAINED') {
    return 'badge badge--attention'
  }
  if (status === 'RUNNING' || status === 'CREATED') {
    return 'badge badge--info'
  }
  return 'badge badge--neutral'
}

async function startInvestigation(): Promise<void> {
  if (requestState.value === 'starting') {
    return
  }

  requestState.value = 'starting'
  requestError.value = null

  try {
    run.value = await startCandidateInvestigation(props.candidateId)
    requestState.value = 'idle'
  } catch (error) {
    requestError.value = error
    requestState.value = 'error'
  }
}
</script>

<template>
  <section
    id="candidate-agent-investigation"
    class="candidate-detail-panel candidate-section-surface"
    role="tabpanel"
    aria-labelledby="candidate-tab-investigation"
    :hidden="!isActive"
    :aria-busy="isStarting"
  >
    <header class="candidate-investigation-header">
      <div class="candidate-investigation-header-row">
        <h2 id="candidate-agent-investigation-heading">AI Investigation</h2>
        <span
          v-if="presentation != null"
          class="candidate-investigation-status"
          :class="investigationStatusBadgeClass(presentation.status)"
        >
          {{ presentation.statusLabel }}
        </span>
      </div>

      <p v-if="presentation == null" class="candidate-helper">
        Analyze the Candidate using its recorded evidence and enterprise context.
      </p>
      <p v-else class="candidate-helper">
        AI-generated assessment based on available evidence and context. Human
        validation is required for a governance decision.
      </p>
    </header>

    <section
      v-if="presentation == null"
      class="candidate-investigation-start"
      aria-labelledby="candidate-agent-investigation-heading"
    >
      <div class="candidate-investigation-actions">
        <button
          type="button"
          class="button"
          :disabled="isStarting"
          :aria-busy="isStarting"
          @click="startInvestigation"
        >
          Start Investigation
        </button>
      </div>

      <p class="candidate-helper">
        The investigation can analyze and recommend. It does not validate the
        Candidate or perform governance actions.
      </p>

      <p
        v-if="viewState === 'starting'"
        class="candidate-detail-message"
        role="status"
      >
        Starting investigation.
      </p>
      <p
        v-else-if="viewState === 'request-error'"
        class="candidate-detail-message"
        role="alert"
      >
        {{ requestErrorMessage }}
      </p>
    </section>

    <template v-else>
      <p
        v-if="presentation.stopReasonLabel != null"
        class="candidate-helper"
      >
        Stop reason: {{ presentation.stopReasonLabel }}
      </p>
      <p
        v-if="presentation.status === 'COMPLETED'"
        class="candidate-helper"
      >
        The investigation completed. This is not Candidate validation.
      </p>
      <p
        v-else-if="presentation.status === 'ABSTAINED'"
        class="candidate-helper"
      >
        The investigation stopped without a supported conclusion. This is not
        Candidate rejection.
      </p>
      <p
        v-else-if="presentation.status === 'FAILED'"
        class="candidate-helper"
      >
        The investigation failed. This does not mean the Candidate is invalid.
      </p>
      <p
        v-else-if="presentation.status === 'CREATED'"
        class="candidate-helper"
        role="status"
      >
        The investigation has been created and has not finished.
      </p>
      <p
        v-else-if="presentation.status === 'RUNNING'"
        class="candidate-helper"
        role="status"
      >
        The investigation is running.
      </p>

      <CandidateProvenanceDetails
        summary-label="Run details"
        :rows="statusProvenanceRows"
      />

      <CandidateStructuredAssessment
        v-if="presentation.assessment"
        :assessment="presentation.assessment"
      />

      <div class="candidate-investigation-actions candidate-investigation-actions--secondary">
        <button
          type="button"
          class="button button--secondary"
          :disabled="isStarting"
          :aria-busy="isStarting"
          @click="startInvestigation"
        >
          Run investigation again
        </button>
      </div>
      <p
        v-if="viewState === 'starting'"
        class="candidate-detail-message"
        role="status"
      >
        Starting investigation.
      </p>
      <p
        v-else-if="viewState === 'request-error'"
        class="candidate-detail-message"
        role="alert"
      >
        {{ requestErrorMessage }}
      </p>

      <details class="candidate-disclosure candidate-investigation-details">
        <summary>Investigation details</summary>
        <CandidateAgentToolTrace :executions="presentation.toolExecutions" />
        <CandidateAgentPolicyTrace :decisions="presentation.policyDecisions" />
      </details>
    </template>
  </section>
</template>
