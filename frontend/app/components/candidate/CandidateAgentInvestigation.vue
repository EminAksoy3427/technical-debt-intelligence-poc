<script setup lang="ts">
import type { CandidateEvidenceItem } from '~/types/candidate'
import type { AgentRunResponse } from '~/types/agentRunApi'
import { toAgentInvestigationPresentation } from '~/utils/mapAgentRun'
import {
  resolveAgentInvestigationRequestError,
  resolveAgentInvestigationViewState,
  type AgentInvestigationRequestState,
} from '~/utils/resolveAgentInvestigationViewState'

const props = defineProps<{
  candidateId: string
  evidence: CandidateEvidenceItem[]
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
    class="candidate-detail-region"
    aria-labelledby="candidate-agent-investigation-heading"
    :aria-busy="isStarting"
  >
    <h2 id="candidate-agent-investigation-heading" class="candidate-region-heading">
      Agent Investigation
    </h2>

    <section
      class="candidate-detail-section"
      aria-labelledby="candidate-investigation-action-heading"
    >
      <h3 id="candidate-investigation-action-heading">Start investigation</h3>
      <p class="candidate-section-introduction">
        Investigate this Candidate by gathering and interpreting existing evidence and
        context. The result is a structured assessment. It does not validate the
        Candidate, create TechnicalDebt, approve actions, or execute writes.
      </p>
      <p class="candidate-section-introduction">
        Human validation is a later lifecycle step and is not available here.
      </p>

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

    <template v-if="presentation">
      <section
        class="candidate-detail-section"
        aria-labelledby="candidate-investigation-status-heading"
      >
        <h3 id="candidate-investigation-status-heading">Investigation status</h3>
        <p class="candidate-section-introduction">
          Status describes this investigation run, not Candidate validity.
        </p>

        <dl class="candidate-detail-list candidate-detail-list--scan">
          <div>
            <dt>Status</dt>
            <dd>
              <span class="badge badge--neutral">{{ presentation.statusLabel }}</span>
              <span class="candidate-identifier">{{ presentation.status }}</span>
            </dd>
          </div>
          <div>
            <dt>Investigation ID</dt>
            <dd class="candidate-identifier candidate-breakable">{{ presentation.agentRunId }}</dd>
          </div>
          <div v-if="presentation.stopReasonLabel != null">
            <dt>Stop reason</dt>
            <dd>
              {{ presentation.stopReasonLabel }}
              <span class="candidate-identifier">{{ presentation.stopReason }}</span>
            </dd>
          </div>
          <div>
            <dt>Created at</dt>
            <dd>{{ presentation.createdAt }}</dd>
          </div>
          <div v-if="presentation.startedAt != null">
            <dt>Started at</dt>
            <dd>{{ presentation.startedAt }}</dd>
          </div>
          <div v-if="presentation.completedAt != null">
            <dt>Completed at</dt>
            <dd>{{ presentation.completedAt }}</dd>
          </div>
        </dl>

        <p
          v-if="presentation.status === 'COMPLETED'"
          class="candidate-summary-note"
        >
          The investigation completed. This is not Candidate validation.
        </p>
        <p
          v-else-if="presentation.status === 'ABSTAINED'"
          class="candidate-summary-note"
        >
          The investigation stopped without a supported conclusion. This is not
          Candidate rejection.
        </p>
        <p
          v-else-if="presentation.status === 'FAILED'"
          class="candidate-summary-note"
        >
          The investigation failed. This does not mean the Candidate is invalid.
        </p>
        <p
          v-else-if="presentation.status === 'CREATED'"
          class="candidate-summary-note"
        >
          The investigation has been created and has not finished.
        </p>
        <p
          v-else-if="presentation.status === 'RUNNING'"
          class="candidate-summary-note"
        >
          The investigation is running.
        </p>
      </section>

      <CandidateStructuredAssessment
        v-if="presentation.assessment"
        :assessment="presentation.assessment"
      />

      <CandidateAgentToolTrace :executions="presentation.toolExecutions" />
      <CandidateAgentPolicyTrace :decisions="presentation.policyDecisions" />
    </template>
  </section>
</template>
