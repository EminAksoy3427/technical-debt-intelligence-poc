<script setup lang="ts">
import {
  candidateGovernanceStateLabels,
  humanDecisionTypeLabels,
  type CandidateGovernancePresentation,
} from '~/types/candidate'
import type { HumanDecisionType } from '~/types/humanValidationApi'
import { availableHumanValidationActions } from '~/utils/availableHumanValidationActions'
import {
  buildHumanValidationRequest,
  humanValidationClientValidationMessage,
} from '~/utils/buildHumanValidationRequest'
import {
  humanValidationSubmitMessage,
  submitHumanValidationDecision,
  type HumanValidationSubmitStatus,
} from '~/utils/submitHumanValidationDecision'

const props = defineProps<{
  candidateId: string
  governance: CandidateGovernancePresentation
  refreshCandidate: () => Promise<unknown>
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
    class="candidate-detail-region"
    aria-labelledby="candidate-human-validation-heading"
    :aria-busy="isSubmitting"
  >
    <h2 id="candidate-human-validation-heading" class="candidate-region-heading">
      Human Validation
    </h2>

    <section
      class="candidate-detail-section"
      aria-labelledby="candidate-governance-state-heading"
    >
      <h3 id="candidate-governance-state-heading">Persisted governance</h3>
      <p class="candidate-section-introduction">
        Human Validation classifies this Candidate. It is not Agent Investigation,
        not Policy ALLOW, and not L4 approval.
      </p>

      <dl class="candidate-detail-list candidate-detail-list--scan">
        <div>
          <dt>Governance state</dt>
          <dd>
            <span class="badge badge--neutral">{{
              candidateGovernanceStateLabels[governance.state]
            }}</span>
            <span class="candidate-identifier">{{ governance.state }}</span>
          </dd>
        </div>
        <div>
          <dt>Revision</dt>
          <dd>{{ governance.revision }}</dd>
        </div>
      </dl>

      <template v-if="governance.technicalDebt">
        <p class="candidate-summary-note">
          A VALIDATE decision created a REGISTERED TechnicalDebt record.
        </p>
        <p>
          <NuxtLink
            class="candidate-reference-link"
            :to="`/technical-debts/${governance.technicalDebt.technicalDebtId}`"
          >
            View Technical Debt
          </NuxtLink>
        </p>
        <dl class="candidate-detail-list candidate-detail-list--scan">
          <div>
            <dt>TechnicalDebt ID</dt>
            <dd class="candidate-identifier candidate-breakable">
              {{ governance.technicalDebt.technicalDebtId }}
            </dd>
          </div>
          <div>
            <dt>Lifecycle status</dt>
            <dd>
              <span class="badge badge--neutral">Registered</span>
              <span class="candidate-identifier">{{
                governance.technicalDebt.lifecycleStatus
              }}</span>
            </dd>
          </div>
          <div>
            <dt>Created at</dt>
            <dd>{{ governance.technicalDebt.createdAt }}</dd>
          </div>
        </dl>
      </template>
    </section>

    <section
      class="candidate-detail-section"
      aria-labelledby="candidate-decision-history-heading"
    >
      <h3 id="candidate-decision-history-heading">Decision history</h3>
      <p class="candidate-section-introduction">
        Persisted Human Validation decisions for this Candidate. Audit actor is
        server-owned attribution, not verified employee identity.
      </p>

      <p
        v-if="orderedDecisions.length === 0"
        class="candidate-summary-note"
      >
        No Human Validation decisions have been recorded.
      </p>
      <ol v-else class="candidate-membership-list candidate-membership-list--cards">
        <li
          v-for="decision in orderedDecisions"
          :key="decision.humanDecisionId"
          class="human-decision-item"
        >
          <dl class="candidate-detail-list candidate-detail-list--scan">
            <div>
              <dt>Decision</dt>
              <dd>
                <span class="badge badge--neutral">{{
                  humanDecisionTypeLabels[decision.decision]
                }}</span>
                <span class="candidate-identifier">{{ decision.decision }}</span>
              </dd>
            </div>
            <div>
              <dt>Sequence</dt>
              <dd>{{ decision.sequenceNumber }}</dd>
            </div>
            <div>
              <dt>Created at</dt>
              <dd>{{ decision.createdAt }}</dd>
            </div>
            <div>
              <dt>Audit actor</dt>
              <dd class="candidate-breakable">{{ decision.actorReference }}</dd>
            </div>
            <div v-if="decision.rationale" class="candidate-fact-span">
              <dt>Rationale</dt>
              <dd>{{ decision.rationale }}</dd>
            </div>
            <div v-if="decision.requestedInformation" class="candidate-fact-span">
              <dt>Requested information</dt>
              <dd>{{ decision.requestedInformation }}</dd>
            </div>
          </dl>
        </li>
      </ol>
    </section>

    <section
      v-if="submitStatus === 'unavailable'"
      class="candidate-detail-section"
      aria-labelledby="candidate-human-validation-unavailable-heading"
    >
      <h3 id="candidate-human-validation-unavailable-heading">Human Validation unavailable</h3>
      <p class="candidate-detail-message" role="alert">
        Human Validation is not available.
      </p>
    </section>

    <section
      v-else-if="submitStatus === 'success-refresh-failed'"
      class="candidate-detail-section"
      aria-labelledby="candidate-human-validation-refresh-failed-heading"
    >
      <h3 id="candidate-human-validation-refresh-failed-heading">Governance refresh</h3>
      <p class="candidate-detail-message" role="alert">
        {{ humanValidationSubmitMessage('success-refresh-failed') }}
      </p>
    </section>

    <section
      v-else-if="submitStatus === 'conflict-refresh-failed'"
      class="candidate-detail-section"
      aria-labelledby="candidate-human-validation-conflict-refresh-failed-heading"
    >
      <h3 id="candidate-human-validation-conflict-refresh-failed-heading">Governance refresh</h3>
      <p class="candidate-detail-message" role="alert">
        {{ humanValidationSubmitMessage('conflict-refresh-failed') }}
      </p>
    </section>

    <section
      v-else-if="actionsAvailable"
      class="candidate-detail-section"
      aria-labelledby="candidate-human-validation-form-heading"
    >
      <h3 id="candidate-human-validation-form-heading">Record a decision</h3>
      <p class="candidate-section-introduction">
        An authorized human records VALIDATE, REJECT, or REQUEST_INFO. The server
        owns actor identity and remains the authority for the resulting state.
      </p>

      <div class="human-validation-choice" role="group" aria-label="Human Validation decision">
        <button
          v-for="action in availableActions"
          :key="action"
          type="button"
          class="button button--secondary"
          :aria-pressed="selectedDecision === action"
          :disabled="isSubmitting"
          @click="selectDecision(action)"
        >
          {{ humanDecisionTypeLabels[action] }}
        </button>
      </div>

      <form class="human-validation-form" @submit.prevent="submitDecision">
        <label
          v-if="selectedDecision === 'VALIDATE' || selectedDecision === 'REJECT'"
          class="decision-field"
        >
          <span>Rationale</span>
          <textarea
            v-model="rationale"
            :disabled="isSubmitting"
            rows="4"
          />
        </label>

        <label v-else-if="selectedDecision === 'REQUEST_INFO'" class="decision-field">
          <span>Requested information</span>
          <textarea
            v-model="requestedInformation"
            :disabled="isSubmitting"
            rows="4"
          />
        </label>

        <div class="human-validation-submit">
          <button
            type="submit"
            class="button"
            :disabled="isSubmitting"
            :aria-busy="isSubmitting"
          >
            Submit decision
          </button>
        </div>
      </form>

      <p
        v-if="isSubmitting"
        class="candidate-detail-message"
        role="status"
      >
        Submitting Human Validation.
      </p>
      <p
        v-else-if="statusMessage"
        class="candidate-detail-message"
        :role="statusRole"
      >
        {{ statusMessage }}
      </p>
    </section>
  </section>
</template>
