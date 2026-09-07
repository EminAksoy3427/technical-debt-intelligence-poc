<script setup lang="ts">
import { candidateAssetTypeDisplayLabel } from '~/types/candidate'
import { formatDisplayTimestamp } from '~/utils/candidateDetailDisplay'
import { toTechnicalDebtDetailPresentation } from '~/utils/mapTechnicalDebt'
import { resolveTechnicalDebtDetailViewState } from '~/utils/resolveTechnicalDebtDetailViewState'
import {
  displayRecordedValue,
  hasRecordedValue,
  humanDecisionTypeDisplayLabel,
} from '~/utils/technicalDebtDisplay'
import {
  technicalDebtsCreationDecisionIntroduction,
  technicalDebtsDetailErrorExplanation,
  technicalDebtsDetailErrorTitle,
  technicalDebtsDetailInvalidExplanation,
  technicalDebtsDetailInvalidTitle,
  technicalDebtsDetailLoading,
  technicalDebtsDetailNotFoundExplanation,
  technicalDebtsDetailNotFoundTitle,
  technicalDebtsReviewCandidatesLabel,
  technicalDebtsSourceCandidateIntroduction,
} from '~/utils/technicalDebtPageCopy'

const route = useRoute()
const { getTechnicalDebt } = useTechnicalDebtApi()

const technicalDebtId = computed(() => String(route.params.id ?? ''))

const { data, pending, error, refresh } = await useAsyncData(
  () => `technical-debt-detail:${technicalDebtId.value}`,
  () => getTechnicalDebt(technicalDebtId.value),
  { server: false },
)

const viewState = computed(() =>
  resolveTechnicalDebtDetailViewState({
    pending: pending.value,
    error: error.value,
    detail: data.value,
    requestedTechnicalDebtId: technicalDebtId.value,
  }),
)

const presentation = computed(() => {
  if (viewState.value !== 'success' || data.value == null) {
    return null
  }

  return toTechnicalDebtDetailPresentation(data.value)
})

const creationDecisionRows = computed(() => {
  const decision = presentation.value?.creationHumanDecision
  if (decision == null) {
    return []
  }

  return [
    { label: 'HumanDecision ID', value: decision.humanDecisionId },
    { label: 'Decision', value: decision.decision },
    { label: 'Created at (raw)', value: decision.createdAt },
  ]
})
</script>

<template>
  <section class="page-section technical-debt-detail candidate-detail" aria-labelledby="technical-debt-title">
    <template v-if="viewState === 'loading'">
      <nav class="candidate-breadcrumb" aria-label="Breadcrumb">
        <ol>
          <li>
            <NuxtLink to="/technical-debts">Technical Debts</NuxtLink>
          </li>
          <li aria-current="page">TechnicalDebt</li>
        </ol>
      </nav>
      <h1 id="technical-debt-title">TechnicalDebt</h1>
      <p class="technical-debt-status" role="status">{{ technicalDebtsDetailLoading }}</p>
    </template>

    <template v-else-if="viewState === 'not-found'">
      <nav class="candidate-breadcrumb" aria-label="Breadcrumb">
        <ol>
          <li>
            <NuxtLink to="/technical-debts">Technical Debts</NuxtLink>
          </li>
          <li aria-current="page">TechnicalDebt</li>
        </ol>
      </nav>
      <h1 id="technical-debt-title">{{ technicalDebtsDetailNotFoundTitle }}</h1>
      <p class="page-introduction">{{ technicalDebtsDetailNotFoundExplanation }}</p>
      <p class="technical-debt-detail-actions">
        <NuxtLink to="/technical-debts" class="button button--secondary">
          Back to Technical Debts
        </NuxtLink>
      </p>
    </template>

    <template v-else-if="viewState === 'invalid-identifier'">
      <nav class="candidate-breadcrumb" aria-label="Breadcrumb">
        <ol>
          <li>
            <NuxtLink to="/technical-debts">Technical Debts</NuxtLink>
          </li>
          <li aria-current="page">TechnicalDebt</li>
        </ol>
      </nav>
      <h1 id="technical-debt-title">{{ technicalDebtsDetailInvalidTitle }}</h1>
      <p class="page-introduction">{{ technicalDebtsDetailInvalidExplanation }}</p>
      <p class="technical-debt-detail-actions">
        <NuxtLink to="/technical-debts" class="button button--secondary">
          Back to Technical Debts
        </NuxtLink>
      </p>
    </template>

    <template v-else-if="viewState === 'error'">
      <nav class="candidate-breadcrumb" aria-label="Breadcrumb">
        <ol>
          <li>
            <NuxtLink to="/technical-debts">Technical Debts</NuxtLink>
          </li>
          <li aria-current="page">TechnicalDebt</li>
        </ol>
      </nav>
      <h1 id="technical-debt-title">{{ technicalDebtsDetailErrorTitle }}</h1>
      <p class="page-introduction">{{ technicalDebtsDetailErrorExplanation }}</p>
      <p class="technical-debt-detail-actions">
        <NuxtLink to="/candidates" class="button button--secondary">
          {{ technicalDebtsReviewCandidatesLabel }}
        </NuxtLink>
      </p>
    </template>

    <template v-else-if="presentation">
      <TechnicalDebtDetailHeader :presentation="presentation" />

      <section
        class="candidate-section-surface technical-debt-detail-section"
        aria-labelledby="technical-debt-source-heading"
      >
        <h2 id="technical-debt-source-heading">Source Candidate</h2>
        <p class="candidate-section-note">{{ technicalDebtsSourceCandidateIntroduction }}</p>
        <dl class="candidate-fact-list">
          <div>
            <dt>Hypothesis</dt>
            <dd>{{ displayRecordedValue(presentation.sourceCandidate.hypothesis) }}</dd>
          </div>
          <div>
            <dt>Canonical asset</dt>
            <dd>
              <span class="candidate-asset-line">
                <span>{{
                  displayRecordedValue(presentation.sourceCandidate.canonicalAssetKey)
                }}</span>
                <span class="candidate-type-badge">{{
                  candidateAssetTypeDisplayLabel(
                    presentation.sourceCandidate.canonicalAssetType,
                  )
                }}</span>
              </span>
            </dd>
          </div>
          <div>
            <dt>Correlation rationale</dt>
            <dd>{{
              displayRecordedValue(presentation.sourceCandidate.correlationRationale)
            }}</dd>
          </div>
        </dl>
        <p class="technical-debt-detail-actions">
          <NuxtLink
            class="candidate-reference-link"
            :to="`/candidates/${presentation.sourceCandidate.candidateId}`"
          >
            Open Candidate
          </NuxtLink>
        </p>
      </section>

      <section
        class="candidate-section-surface technical-debt-detail-section"
        aria-labelledby="technical-debt-decision-heading"
      >
        <h2 id="technical-debt-decision-heading">Creation VALIDATE decision</h2>
        <p class="candidate-section-note">{{ technicalDebtsCreationDecisionIntroduction }}</p>
        <dl class="candidate-fact-list">
          <div>
            <dt>Decision</dt>
            <dd>{{ humanDecisionTypeDisplayLabel(presentation.creationHumanDecision.decision) }}</dd>
          </div>
          <div>
            <dt>Sequence</dt>
            <dd>{{ presentation.creationHumanDecision.sequenceNumber }}</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>
              <time :datetime="presentation.creationHumanDecision.createdAt">{{
                formatDisplayTimestamp(presentation.creationHumanDecision.createdAt)
              }}</time>
            </dd>
          </div>
          <div>
            <dt>Audit actor</dt>
            <dd class="candidate-breakable">
              {{ displayRecordedValue(presentation.creationHumanDecision.actorReference) }}
            </dd>
          </div>
          <div v-if="hasRecordedValue(presentation.creationHumanDecision.rationale)">
            <dt>Rationale</dt>
            <dd>{{ presentation.creationHumanDecision.rationale }}</dd>
          </div>
        </dl>
        <CandidateProvenanceDetails
          :rows="creationDecisionRows"
          summary-label="Technical details"
        />
      </section>

      <TechnicalDebtActionPreparation
        :technical-debt-id="presentation.technicalDebtId"
        :action-proposals="presentation.actionProposals"
        :refresh-technical-debt="refresh"
      />

      <TechnicalDebtActionWorkbench
        :presentation="presentation"
        :refresh-technical-debt="refresh"
      />
    </template>
  </section>
</template>
