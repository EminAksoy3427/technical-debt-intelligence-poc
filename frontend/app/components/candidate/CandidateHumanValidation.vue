<script setup lang="ts">
import {
  candidateGovernanceStateLabels,
  humanDecisionTypeLabels,
  type CandidateGovernancePresentation,
  type CandidateHumanDecisionItem,
} from '~/types/candidate'
import type { HumanDecisionType } from '~/types/humanValidationApi'
import { formatDisplayTimestamp } from '~/utils/candidateDetailDisplay'
import { availableHumanValidationActions } from '~/utils/availableHumanValidationActions'
import {
  buildHumanValidationRequest,
  humanValidationClientValidationMessage,
} from '~/utils/buildHumanValidationRequest'
import {
  formatHumanValidationEvidenceCount,
  HUMAN_VALIDATION_DISTINCTION,
  HUMAN_VALIDATION_CLOSED_HELPER,
  HUMAN_VALIDATION_HEADER_HELPER,
  HUMAN_VALIDATION_REJECT_HELPER,
  HUMAN_VALIDATION_REQUEST_INFO_HELPER,
  HUMAN_VALIDATION_SELECT_PROMPT,
  HUMAN_VALIDATION_SUBMIT_HELPER,
  HUMAN_VALIDATION_VALIDATE_CONSEQUENCE,
  humanDecisionResultingGovernanceLabel,
  humanValidationDecisionDescriptions,
  humanValidationSubmitLabel,
} from '~/utils/humanValidationDecisionCopy'
import {
  humanValidationSubmitMessage,
  submitHumanValidationDecision,
  type HumanValidationSubmitStatus,
} from '~/utils/submitHumanValidationDecision'

const props = defineProps<{
  candidateId: string
  candidateTitle: string
  evidenceCount: number
  governance: CandidateGovernancePresentation
  refreshCandidate: () => Promise<unknown>
  isActive: boolean
}>()

const { createHumanDecision } = useHumanValidationApi()

const selectedDecision = ref<HumanDecisionType | null>(null)
const rationale = ref('')
const requestedInformation = ref('')
const requestState = ref<'idle' | 'submitting'>('idle')
const submitStatus = ref<Exclude<HumanValidationSubmitStatus, 'success'> | null>(null)
const clientValidationMessage = ref('')

const isSubmitting = computed(() => requestState.value === 'submitting')
const availableActions = computed(() => availableHumanValidationActions(props.governance.state))
const actionsAvailable = computed(
  () =>
    availableActions.value.length > 0 &&
    submitStatus.value !== 'unavailable' &&
    submitStatus.value !== 'success-refresh-failed' &&
    submitStatus.value !== 'conflict-refresh-failed',
)
const orderedDecisions = computed(() =>
  [...props.governance.decisions].sort((left, right) => left.sequenceNumber - right.sequenceNumber),
)
const evidenceCountLabel = computed(() => formatHumanValidationEvidenceCount(props.evidenceCount))
const submitLabel = computed(() =>
  selectedDecision.value == null ? '' : humanValidationSubmitLabel(selectedDecision.value),
)
const selectedFieldHintId = computed(() => {
  if (selectedDecision.value === 'REQUEST_INFO') {
    return 'human-validation-requested-information-hint'
  }
  if (selectedDecision.value === 'VALIDATE' || selectedDecision.value === 'REJECT') {
    return 'human-validation-rationale-hint'
  }
  return undefined
})
const statusMessageId = 'human-validation-status'
const fieldDescribedBy = computed(() => {
  const ids = [selectedFieldHintId.value]
  if (statusMessage.value) {
    ids.push(statusMessageId)
  }
  return ids.filter((id): id is string => id != null).join(' ')
})

const statusMessage = computed(() => {
  if (clientValidationMessage.value) {
    return clientValidationMessage.value
  }
  if (submitStatus.value == null) {
    return ''
  }
  return humanValidationSubmitMessage(submitStatus.value)
})

const statusRole = computed(() => {
  if (isSubmitting.value) {
    return 'status'
  }
  return statusMessage.value ? 'alert' : undefined
})

const governanceDetailRows = computed(() => [
  { label: 'Governance state', value: props.governance.state },
  { label: 'Governance revision', value: String(props.governance.revision) },
])

const technicalDebtRows = computed(() => {
  const technicalDebt = props.governance.technicalDebt
  if (technicalDebt == null) {
    return []
  }

  return [
    { label: 'TechnicalDebt ID', value: technicalDebt.technicalDebtId },
    { label: 'Lifecycle status', value: technicalDebt.lifecycleStatus },
    { label: 'Created', value: formatDisplayTimestamp(technicalDebt.createdAt) },
    { label: 'Created at (raw)', value: technicalDebt.createdAt },
  ]
})

function decisionHistoryRows(decision: CandidateHumanDecisionItem): { label: string; value: string }[] {
  return [
    { label: 'Decision ID', value: decision.humanDecisionId },
    { label: 'Sequence', value: String(decision.sequenceNumber) },
    { label: 'Decision type', value: decision.decision },
    { label: 'Audit actor', value: decision.actorReference },
    { label: 'Created at (raw)', value: decision.createdAt },
  ]
}

function selectDecision(decision: HumanDecisionType): void {
  selectedDecision.value = decision
  clientValidationMessage.value = ''
}

function clearDecisionForm(): void {
  selectedDecision.value = null
  rationale.value = ''
  requestedInformation.value = ''
  clientValidationMessage.value = ''
}

async function submitDecision(): Promise<void> {
  if (requestState.value === 'submitting') {
    return
  }

  const decision = selectedDecision.value
  if (decision == null) {
    clientValidationMessage.value = 'Choose a Human Validation decision.'
    return
  }

  const validationMessage = humanValidationClientValidationMessage(
    decision,
    rationale.value,
    requestedInformation.value,
  )
  if (validationMessage != null) {
    clientValidationMessage.value = validationMessage
    return
  }

  requestState.value = 'submitting'
  clientValidationMessage.value = ''
  submitStatus.value = null

  const result = await submitHumanValidationDecision({
    candidateId: props.candidateId,
    payload: buildHumanValidationRequest({
      decision,
      expectedGovernanceRevision: props.governance.revision,
      rationale: rationale.value,
      requestedInformation: requestedInformation.value,
    }),
    createHumanDecision,
    refreshCandidate: props.refreshCandidate,
  })

  requestState.value = 'idle'

  if (result === 'success') {
    clearDecisionForm()
    return
  }

  if (result === 'success-refresh-failed') {
    clearDecisionForm()
  }

  submitStatus.value = result
}
</script>

<template>
  <section
    id="candidate-human-validation"
    class="candidate-detail-panel candidate-section-surface"
    role="tabpanel"
    aria-labelledby="candidate-tab-validation"
    :hidden="!isActive"
    :aria-busy="isSubmitting"
  >
    <header class="candidate-investigation-header">
      <div class="candidate-investigation-header-row">
        <h2 id="candidate-human-validation-heading">Human Validation</h2>
        <span class="badge badge--neutral">{{
          candidateGovernanceStateLabels[governance.state]
        }}</span>
        <span class="visually-hidden">Governance {{ governance.state }}</span>
      </div>
      <p v-if="availableActions.length > 0" class="candidate-helper">
        {{ HUMAN_VALIDATION_HEADER_HELPER }}
      </p>
      <p v-else class="candidate-helper">{{ HUMAN_VALIDATION_CLOSED_HELPER }}</p>
      <p class="candidate-helper">{{ HUMAN_VALIDATION_DISTINCTION }}</p>
    </header>

    <section
      class="candidate-detail-block"
      aria-labelledby="candidate-validation-context-heading"
    >
      <h3 id="candidate-validation-context-heading">Decision context</h3>
      <dl class="candidate-metric-row human-validation-context">
        <div class="candidate-metric">
          <dt>Candidate</dt>
          <dd>{{ candidateTitle }}</dd>
        </div>
        <div class="candidate-metric">
          <dt>Evidence</dt>
          <dd>{{ evidenceCountLabel }}</dd>
        </div>
      </dl>
      <CandidateProvenanceDetails
        summary-label="Technical details"
        :rows="governanceDetailRows"
      />
    </section>

    <section
      v-if="submitStatus === 'unavailable'"
      class="candidate-detail-block"
      aria-labelledby="candidate-human-validation-unavailable-heading"
    >
      <h3 id="candidate-human-validation-unavailable-heading">Human Validation unavailable</h3>
      <p class="candidate-detail-message" role="alert">
        Human Validation is not available.
      </p>
    </section>

    <section
      v-else-if="submitStatus === 'success-refresh-failed'"
      class="candidate-detail-block"
      aria-labelledby="candidate-human-validation-refresh-failed-heading"
    >
      <h3 id="candidate-human-validation-refresh-failed-heading">Governance refresh</h3>
      <p class="candidate-detail-message" role="alert">
        {{ humanValidationSubmitMessage('success-refresh-failed') }}
      </p>
    </section>

    <section
      v-else-if="submitStatus === 'conflict-refresh-failed'"
      class="candidate-detail-block"
      aria-labelledby="candidate-human-validation-conflict-refresh-failed-heading"
    >
      <h3 id="candidate-human-validation-conflict-refresh-failed-heading">Governance refresh</h3>
      <p class="candidate-detail-message" role="alert">
        {{ humanValidationSubmitMessage('conflict-refresh-failed') }}
      </p>
    </section>

    <section
      v-else-if="actionsAvailable"
      class="candidate-detail-block"
      aria-labelledby="candidate-human-validation-form-heading"
    >
      <form class="human-validation-form" @submit.prevent="submitDecision">
        <fieldset class="human-validation-selector">
          <legend id="candidate-human-validation-form-heading">Record a decision</legend>
          <div class="human-validation-choice">
            <label
              v-for="action in availableActions"
              :key="action"
              class="human-validation-option"
              :class="{
                'human-validation-option--selected': selectedDecision === action,
              }"
            >
              <input
                type="radio"
                name="human-validation-decision"
                :value="action"
                :checked="selectedDecision === action"
                :disabled="isSubmitting"
                @change="selectDecision(action)"
              />
              <span class="human-validation-option-body">
                <span class="human-validation-option-title-row">
                  <span class="human-validation-option-title">
                    {{ humanDecisionTypeLabels[action] }}
                  </span>
                  <span
                    v-if="selectedDecision === action"
                    class="human-validation-option-selected"
                  >
                    Selected
                  </span>
                </span>
                <span class="human-validation-option-description">
                  {{ humanValidationDecisionDescriptions[action] }}
                </span>
              </span>
            </label>
          </div>
        </fieldset>

        <p
          v-if="selectedDecision == null"
          class="candidate-empty-value"
        >
          {{ HUMAN_VALIDATION_SELECT_PROMPT }}
        </p>

        <div
          v-else-if="selectedDecision === 'VALIDATE' || selectedDecision === 'REJECT'"
          class="decision-field"
        >
          <label for="human-validation-rationale">Rationale</label>
          <p id="human-validation-rationale-hint" class="candidate-helper">
            Explain the basis for this decision.
          </p>
          <p
            v-if="selectedDecision === 'VALIDATE'"
            class="candidate-helper"
          >
            {{ HUMAN_VALIDATION_VALIDATE_CONSEQUENCE }}
          </p>
          <p
            v-else
            class="candidate-helper"
          >
            {{ HUMAN_VALIDATION_REJECT_HELPER }}
          </p>
          <textarea
            id="human-validation-rationale"
            v-model="rationale"
            :disabled="isSubmitting"
            :aria-required="true"
            :aria-invalid="Boolean(clientValidationMessage)"
            :aria-describedby="fieldDescribedBy"
            rows="4"
          />
        </div>

        <div
          v-else-if="selectedDecision === 'REQUEST_INFO'"
          class="decision-field"
        >
          <label for="human-validation-requested-information">Information requested</label>
          <p id="human-validation-requested-information-hint" class="candidate-helper">
            Describe what additional evidence or context is needed.
          </p>
          <p class="candidate-helper">
            {{ HUMAN_VALIDATION_REQUEST_INFO_HELPER }}
          </p>
          <textarea
            id="human-validation-requested-information"
            v-model="requestedInformation"
            :disabled="isSubmitting"
            :aria-required="true"
            :aria-invalid="Boolean(clientValidationMessage)"
            :aria-describedby="fieldDescribedBy"
            rows="4"
          />
        </div>

        <div v-if="selectedDecision != null" class="human-validation-submit">
          <button
            type="submit"
            class="button"
            :disabled="isSubmitting"
            :aria-busy="isSubmitting"
          >
            {{ submitLabel }}
          </button>
          <p class="candidate-helper">{{ HUMAN_VALIDATION_SUBMIT_HELPER }}</p>
        </div>
      </form>

      <p
        v-if="isSubmitting"
        :id="statusMessageId"
        class="candidate-detail-message"
        role="status"
      >
        Submitting Human Validation.
      </p>
      <p
        v-else-if="statusMessage"
        :id="statusMessageId"
        class="candidate-detail-message"
        :role="statusRole"
      >
        {{ statusMessage }}
      </p>
    </section>

    <p
      v-else-if="availableActions.length === 0"
      class="candidate-empty-inline"
    >
      No Human Validation actions are available in the current governance state.
    </p>

    <section
      v-if="governance.technicalDebt"
      class="candidate-detail-block"
      aria-labelledby="candidate-validation-result-heading"
    >
      <h3 id="candidate-validation-result-heading">Result</h3>
      <p class="candidate-helper">
        A VALIDATE decision created a REGISTERED TechnicalDebt record.
      </p>
      <p>
        <NuxtLink
          class="candidate-reference-link"
          :to="`/technical-debts/${governance.technicalDebt.technicalDebtId}`"
        >
          Open TechnicalDebt record
        </NuxtLink>
      </p>
      <CandidateProvenanceDetails
        summary-label="Technical details"
        :rows="technicalDebtRows"
      />
    </section>

    <section
      class="candidate-detail-block"
      aria-labelledby="candidate-decision-history-heading"
    >
      <h3 id="candidate-decision-history-heading">Decision history</h3>
      <p class="candidate-helper">
        Persisted Human Validation decisions for this Candidate. Audit actor is
        server-owned attribution, not verified employee identity.
      </p>

      <p
        v-if="orderedDecisions.length === 0"
        class="candidate-empty-inline"
      >
        No Human Validation decisions have been recorded.
      </p>
      <ol v-else class="candidate-record-list">
        <li
          v-for="decision in orderedDecisions"
          :key="decision.humanDecisionId"
          class="human-decision-item"
        >
          <p class="candidate-record-title">
            {{ humanDecisionTypeLabels[decision.decision] }}
          </p>
          <p class="candidate-record-meta">
            <span>{{ formatDisplayTimestamp(decision.createdAt) }}</span>
            <span>Reviewer {{ decision.actorReference }}</span>
          </p>
          <p v-if="decision.rationale" class="candidate-record-body">
            Rationale: {{ decision.rationale }}
          </p>
          <p v-if="decision.requestedInformation" class="candidate-record-body">
            Information requested: {{ decision.requestedInformation }}
          </p>
          <p class="candidate-record-meta">
            Result: {{ humanDecisionResultingGovernanceLabel(decision.decision) }}
          </p>
          <CandidateProvenanceDetails
            summary-label="Technical details"
            :rows="decisionHistoryRows(decision)"
          />
        </li>
      </ol>
    </section>
  </section>
</template>
