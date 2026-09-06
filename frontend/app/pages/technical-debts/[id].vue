<script setup lang="ts">
import { candidatePoolAssetTypeLabels, humanDecisionTypeLabels } from '~/types/candidate'
import { technicalDebtLifecycleStatusLabels } from '~/types/technicalDebt'
import { toTechnicalDebtDetailPresentation } from '~/utils/mapTechnicalDebt'
import { resolveTechnicalDebtDetailViewState } from '~/utils/resolveTechnicalDebtDetailViewState'

const route = useRoute()
const { getTechnicalDebt } = useTechnicalDebtApi()

const technicalDebtId = computed(() => String(route.params.id ?? ''))

const { data, pending, error } = await useAsyncData(
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
</script>

<template>
  <section class="page-section candidate-detail" aria-labelledby="technical-debt-title">
    <NuxtLink to="/technical-debts" class="back-link">Back to Technical Debts</NuxtLink>

    <template v-if="viewState === 'loading'">
      <p class="eyebrow">TechnicalDebt</p>
      <h1 id="technical-debt-title">TechnicalDebt</h1>
      <p class="candidate-detail-message" role="status">Loading TechnicalDebt details.</p>
    </template>

    <template v-else-if="viewState === 'not-found'">
      <h1 id="technical-debt-title">TechnicalDebt was not found.</h1>
      <p class="page-introduction">The requested TechnicalDebt does not exist.</p>
    </template>

    <template v-else-if="viewState === 'invalid-identifier'">
      <h1 id="technical-debt-title">The TechnicalDebt identifier is invalid.</h1>
      <p class="page-introduction">
        The requested TechnicalDebt identifier is not a valid TechnicalDebt ID.
      </p>
    </template>

    <template v-else-if="viewState === 'error'">
      <h1 id="technical-debt-title">TechnicalDebt details could not be loaded.</h1>
      <p class="page-introduction">TechnicalDebt details could not be loaded. Try again later.</p>
    </template>

    <template v-else-if="presentation">
      <header class="candidate-summary">
        <p class="eyebrow">TechnicalDebt</p>
        <h1 id="technical-debt-title">{{ presentation.sourceCandidate.hypothesis }}</h1>
        <p class="candidate-identifier">
          <span class="candidate-id-label">TechnicalDebt ID</span>
          {{ presentation.technicalDebtId }}
        </p>
        <p class="candidate-summary-note">
          REGISTERED means a human VALIDATE decision created this record. It is
          not remediation approval.
        </p>

        <dl class="candidate-summary-facts">
          <div>
            <dt>Lifecycle status</dt>
            <dd>
              <span class="badge badge--neutral">{{
                technicalDebtLifecycleStatusLabels[presentation.lifecycleStatus]
              }}</span>
              <span class="candidate-identifier">{{ presentation.lifecycleStatus }}</span>
            </dd>
          </div>
          <div>
            <dt>Created at</dt>
            <dd>{{ presentation.createdAt }}</dd>
          </div>
          <div>
            <dt>Canonical asset</dt>
            <dd>
              <span class="candidate-asset-name">{{
                presentation.sourceCandidate.canonicalAssetKey
              }}</span>
              <span class="badge badge--neutral">{{
                candidatePoolAssetTypeLabels[presentation.sourceCandidate.canonicalAssetType]
              }}</span>
            </dd>
          </div>
        </dl>
      </header>

      <section class="candidate-detail-section" aria-labelledby="technical-debt-source-heading">
        <h2 id="technical-debt-source-heading">Source Candidate</h2>
        <p class="candidate-section-introduction">
          Evidence remains on the source Candidate. This page does not copy
          Candidate Evidence into TechnicalDebt-owned evidence.
        </p>
        <dl class="candidate-detail-list candidate-detail-list--scan">
          <div>
            <dt>Candidate ID</dt>
            <dd class="candidate-identifier candidate-breakable">
              {{ presentation.sourceCandidate.candidateId }}
            </dd>
          </div>
          <div>
            <dt>Hypothesis</dt>
            <dd>{{ presentation.sourceCandidate.hypothesis }}</dd>
          </div>
          <div class="candidate-fact-span">
            <dt>Correlation rationale</dt>
            <dd>{{ presentation.sourceCandidate.correlationRationale }}</dd>
          </div>
        </dl>
        <p>
          <NuxtLink
            class="candidate-reference-link"
            :to="`/candidates/${presentation.sourceCandidate.candidateId}`"
          >
            View source Candidate
          </NuxtLink>
        </p>
      </section>

      <section class="candidate-detail-section" aria-labelledby="technical-debt-decision-heading">
        <h2 id="technical-debt-decision-heading">Creation HumanDecision</h2>
        <p class="candidate-section-introduction">
          The VALIDATE decision that created this TechnicalDebt. Audit actor is
          server-owned attribution, not verified employee identity.
        </p>
        <dl class="candidate-detail-list candidate-detail-list--scan">
          <div>
            <dt>Decision</dt>
            <dd>
              <span class="badge badge--neutral">{{
                humanDecisionTypeLabels[presentation.creationHumanDecision.decision]
              }}</span>
              <span class="candidate-identifier">{{
                presentation.creationHumanDecision.decision
              }}</span>
            </dd>
          </div>
          <div>
            <dt>Sequence</dt>
            <dd>{{ presentation.creationHumanDecision.sequenceNumber }}</dd>
          </div>
          <div>
            <dt>Created at</dt>
            <dd>{{ presentation.creationHumanDecision.createdAt }}</dd>
          </div>
          <div>
            <dt>Audit actor</dt>
            <dd class="candidate-breakable">
              {{ presentation.creationHumanDecision.actorReference }}
            </dd>
          </div>
          <div v-if="presentation.creationHumanDecision.rationale" class="candidate-fact-span">
            <dt>Rationale</dt>
            <dd>{{ presentation.creationHumanDecision.rationale }}</dd>
          </div>
        </dl>
      </section>
    </template>
  </section>
</template>
