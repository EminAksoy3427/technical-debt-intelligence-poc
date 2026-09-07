<script setup lang="ts">
import { formatDisplayTimestamp } from '~/utils/candidateDetailDisplay'
import { toActionProposalPresentation } from '~/utils/mapTechnicalDebt'
import {
  actionPreparationSubmitMessage,
  submitActionPreparation,
  type ActionPreparationSubmitStatus,
} from '~/utils/submitActionPreparation'
import {
  actionProposalTargetRepository,
  displayRecordedValue,
  newestActionProposal,
  previousActionProposals,
} from '~/utils/technicalDebtDisplay'
import {
  technicalDebtsActionPreparationCurrentPreviewTitle,
  technicalDebtsActionPreparationEmptyPreview,
  technicalDebtsActionPreparationIntroduction,
  technicalDebtsActionPreparationPrepareHint,
  technicalDebtsActionPreparationPrepareLabel,
  technicalDebtsActionPreparationPreviousHeading,
  technicalDebtsActionPreparationTitle,
} from '~/utils/technicalDebtPageCopy'
import type { ActionProposalPresentation } from '~/types/technicalDebt'

const props = defineProps<{
  technicalDebtId: string
  actionProposals: readonly ActionProposalPresentation[]
  refreshTechnicalDebt: () => Promise<unknown>
}>()

const { prepareActionProposal } = useTechnicalDebtApi()

const requestState = ref<'idle' | 'submitting'>('idle')
const submitStatus = ref<Exclude<ActionPreparationSubmitStatus, 'success'> | null>(null)
const locallyPreparedProposals = ref<ActionProposalPresentation[]>([])

const isSubmitting = computed(() => requestState.value === 'submitting')
const displayedProposals = computed(() => {
  const fromServer = props.actionProposals
  const extras = locallyPreparedProposals.value.filter(
    (local) =>
      !fromServer.some((proposal) => proposal.actionProposalId === local.actionProposalId),
  )
  return [...fromServer, ...extras]
})
const currentPreview = computed(() => newestActionProposal(displayedProposals.value))
const previousProposals = computed(() => previousActionProposals(displayedProposals.value))
const statusMessage = computed(() => {
  if (isSubmitting.value) {
    return 'Preparing GitHub issue preview.'
  }
  if (submitStatus.value == null) {
    return ''
  }
  return actionPreparationSubmitMessage(submitStatus.value)
})
const statusRole = computed(() => {
  if (isSubmitting.value) {
    return 'status'
  }
  return statusMessage.value ? 'alert' : undefined
})

function previewRows(proposal: ActionProposalPresentation) {
  return [
    { label: 'ActionProposal ID', value: proposal.actionProposalId },
    { label: 'Payload fingerprint', value: proposal.payloadFingerprint },
    { label: 'Reconciliation marker', value: proposal.reconciliationMarker },
    { label: 'Prepared at (raw)', value: proposal.createdAt },
  ]
}

async function prepareGitHubIssue() {
  if (isSubmitting.value) {
    return
  }

  requestState.value = 'submitting'
  submitStatus.value = null
  const result = await submitActionPreparation({
    technicalDebtId: props.technicalDebtId,
    prepareActionProposal,
    refreshTechnicalDebt: props.refreshTechnicalDebt,
  })
  if (result.proposal != null) {
    const presentation = toActionProposalPresentation(result.proposal)
    if (
      !locallyPreparedProposals.value.some(
        (proposal) => proposal.actionProposalId === presentation.actionProposalId,
      )
    ) {
      locallyPreparedProposals.value = [...locallyPreparedProposals.value, presentation]
    }
  }
  submitStatus.value = result.status === 'success' ? null : result.status
  requestState.value = 'idle'
}
</script>

<template>
  <section
    class="candidate-section-surface technical-debt-detail-section"
    aria-labelledby="technical-debt-action-preparation-heading"
    :aria-busy="isSubmitting"
  >
    <h2 id="technical-debt-action-preparation-heading">
      {{ technicalDebtsActionPreparationTitle }}
    </h2>
    <p class="candidate-section-note">{{ technicalDebtsActionPreparationIntroduction }}</p>
    <p class="candidate-section-note">{{ technicalDebtsActionPreparationPrepareHint }}</p>

    <p class="technical-debt-detail-actions">
      <button
        type="button"
        class="button"
        :disabled="isSubmitting"
        @click="prepareGitHubIssue"
      >
        {{ technicalDebtsActionPreparationPrepareLabel }}
      </button>
    </p>
    <p
      v-if="statusMessage"
      id="technical-debt-action-preparation-status"
      class="candidate-detail-message"
      :role="statusRole"
    >
      {{ statusMessage }}
    </p>

    <section
      v-if="currentPreview"
      class="action-proposal-preview"
      aria-labelledby="technical-debt-action-preview-heading"
    >
      <h3 id="technical-debt-action-preview-heading">
        {{ technicalDebtsActionPreparationCurrentPreviewTitle }}
      </h3>
      <dl class="candidate-fact-list">
        <div>
          <dt>Target repository</dt>
          <dd>{{
            actionProposalTargetRepository(
              currentPreview.targetRepositoryOwner,
              currentPreview.targetRepositoryName,
            )
          }}</dd>
        </div>
        <div>
          <dt>Action</dt>
          <dd>{{ currentPreview.actionType }}</dd>
        </div>
        <div>
          <dt>Issue title</dt>
          <dd>{{ displayRecordedValue(currentPreview.title) }}</dd>
        </div>
        <div>
          <dt>Issue body</dt>
          <dd>
            <pre class="action-proposal-body">{{ currentPreview.body }}</pre>
          </dd>
        </div>
        <div>
          <dt>Prepared</dt>
          <dd>
            <time :datetime="currentPreview.createdAt">{{
              formatDisplayTimestamp(currentPreview.createdAt)
            }}</time>
          </dd>
        </div>
        <div>
          <dt>Audit actor</dt>
          <dd class="candidate-breakable">
            {{ displayRecordedValue(currentPreview.preparedBy) }}
          </dd>
        </div>
      </dl>
      <CandidateProvenanceDetails
        :rows="previewRows(currentPreview)"
        summary-label="Proposal identity"
      />
    </section>
    <p v-else class="candidate-empty-inline">
      {{ technicalDebtsActionPreparationEmptyPreview }}
    </p>

    <section
      v-if="previousProposals.length > 0"
      class="action-proposal-history"
      aria-labelledby="technical-debt-action-history-heading"
    >
      <h3 id="technical-debt-action-history-heading">
        {{ technicalDebtsActionPreparationPreviousHeading(previousProposals.length) }}
      </h3>
      <ol class="candidate-record-list">
        <li
          v-for="proposal in previousProposals"
          :key="proposal.actionProposalId"
        >
          <p class="candidate-record-title">{{ displayRecordedValue(proposal.title) }}</p>
          <p class="candidate-record-meta">
            <span>{{
              actionProposalTargetRepository(
                proposal.targetRepositoryOwner,
                proposal.targetRepositoryName,
              )
            }}</span>
            <span>{{ proposal.actionType }}</span>
            <time :datetime="proposal.createdAt">{{
              formatDisplayTimestamp(proposal.createdAt)
            }}</time>
          </p>
          <CandidateProvenanceDetails
            :rows="previewRows(proposal)"
            summary-label="Proposal identity"
          />
        </li>
      </ol>
    </section>
  </section>
</template>
