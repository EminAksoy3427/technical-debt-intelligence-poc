<script setup lang="ts">
import { toCandidateListItem } from '~/utils/mapCandidateSummary'
import { resolveOverviewCandidateViewState } from '~/utils/resolveOverviewCandidateViewState'
import { selectCandidatesForReview } from '~/utils/selectCandidatesForReview'
import { summarizeCandidateCollection } from '~/utils/summarizeCandidateCollection'

const { getCandidates } = useCandidateApi()

const { data, pending, error } = await useAsyncData(
  'overview-candidates',
  () => getCandidates(),
  { server: false },
)

const candidates = computed(() => (data.value?.items ?? []).map(toCandidateListItem))

const candidateViewState = computed(() =>
  resolveOverviewCandidateViewState({
    pending: pending.value,
    hasError: Boolean(error.value),
    hasListResponse: data.value != null,
    candidateCount: candidates.value.length,
  }),
)

const collectionSummary = computed(() => summarizeCandidateCollection(candidates.value))

const candidatesForReview = computed(() => selectCandidatesForReview(candidates.value))

const assetTypesLabel = computed(() => {
  const types = collectionSummary.value.assetTypesRepresented
  if (types.length === 0) {
    return 'None in the current collection'
  }

  return types.map((item) => item.label).join(', ')
})
</script>

<template>
  <section class="page-section overview-page" aria-labelledby="overview-title">
    <header class="page-header page-header--queue overview-hero">
      <h1 id="overview-title">Overview</h1>
      <p class="overview-subtitle">Technical debt intelligence and governance</p>
      <p class="page-introduction">
        Correlate engineering and operational signals into reviewable Candidates,
        investigate them with governed AI, and record human governance decisions.
      </p>
      <p class="overview-hero-actions">
        <NuxtLink to="/candidates" class="button">Review Candidates</NuxtLink>
      </p>
    </header>

    <section
      class="overview-section overview-candidate-intelligence"
      aria-labelledby="overview-candidate-intelligence-heading"
    >
      <header class="overview-section-header">
        <h2 id="overview-candidate-intelligence-heading">Candidate intelligence</h2>
        <p class="overview-section-note">
          These counts are from the current Candidate collection. They are not
          system-wide signal or evidence totals.
        </p>
      </header>

      <p v-if="candidateViewState === 'loading'" class="overview-inline-status" role="status">
        Loading candidate summary.
      </p>

      <p v-else-if="candidateViewState === 'error'" class="overview-inline-status" role="alert">
        Candidates could not be loaded.
      </p>

      <template v-else>
        <dl class="overview-metric-row">
          <div class="overview-metric">
            <dt>Candidates</dt>
            <dd>{{ collectionSummary.candidateCount }}</dd>
          </div>
          <div class="overview-metric">
            <dt>Signals represented</dt>
            <dd>{{ collectionSummary.signalsRepresented }}</dd>
          </div>
          <div class="overview-metric">
            <dt>Evidence represented</dt>
            <dd>{{ collectionSummary.evidenceRepresented }}</dd>
          </div>
          <div class="overview-metric">
            <dt>Asset types represented</dt>
            <dd>{{ collectionSummary.assetTypesRepresented.length }}</dd>
            <p class="overview-metric-detail">{{ assetTypesLabel }}</p>
          </div>
        </dl>

        <p class="overview-section-actions">
          <NuxtLink to="/candidates" class="button">Review Candidates</NuxtLink>
        </p>
      </template>
    </section>

    <section
      class="overview-section"
      aria-labelledby="overview-candidates-for-review-heading"
    >
      <header class="overview-section-header overview-section-header--split">
        <div>
          <h2 id="overview-candidates-for-review-heading">Candidates for review</h2>
          <p class="overview-section-note">
            Shown in the Candidate list order. That order is a stable factual
            sequence, not priority or recency.
          </p>
        </div>
        <NuxtLink to="/candidates" class="candidate-action-link">View all Candidates</NuxtLink>
      </header>

      <p v-if="candidateViewState === 'loading'" class="overview-inline-status" role="status">
        Loading Candidates for review.
      </p>

      <p v-else-if="candidateViewState === 'error'" class="overview-inline-status" role="alert">
        Candidates for review could not be loaded.
      </p>

      <p v-else-if="candidateViewState === 'empty'" class="overview-inline-status" role="status">
        No Candidates are currently available for review.
      </p>

      <OverviewCandidateReviewList
        v-else
        :candidates="candidatesForReview"
      />
    </section>

    <OverviewOperatingModel />

    <div class="overview-split layout-columns">
      <OverviewSignalSources />
      <OverviewGovernanceBoundary />
    </div>

    <div class="overview-split layout-columns">
      <section class="overview-section" aria-labelledby="overview-technical-debts-heading">
        <h2 id="overview-technical-debts-heading">Technical Debts</h2>
        <p class="overview-section-note">
          Governed records created through Human Validation. A Candidate is not
          TechnicalDebt until a human VALIDATE decision.
        </p>
        <p class="overview-section-actions">
          <NuxtLink to="/technical-debts" class="button button--secondary">
            View Technical Debts
          </NuxtLink>
        </p>
      </section>

      <section class="overview-section" aria-labelledby="overview-explore-sources-heading">
        <h2 id="overview-explore-sources-heading">Sources</h2>
        <p class="overview-section-note">
          Registered connector inventory. Registration is not a live health check
          and is not a successful ingestion result.
        </p>
        <p class="overview-section-actions">
          <NuxtLink to="/sources" class="button button--secondary">Explore Sources</NuxtLink>
        </p>
      </section>
    </div>
  </section>
</template>
