<script setup lang="ts">
import {
  candidateAssetCriticalityLabels,
  candidateAssetLifecycleStatusLabels,
  candidatePoolAssetTypeLabels,
} from '~/types/candidate'
import { toCandidateDetailPresentation } from '~/utils/mapCandidateDetail'
import { resolveCandidateDetailViewState } from '~/utils/resolveCandidateDetailViewState'

const route = useRoute()
const { getCandidate } = useCandidateApi()

const candidateId = computed(() => String(route.params.id ?? ''))

const { data, pending, error } = await useAsyncData(
  () => `candidate-detail:${candidateId.value}`,
  () => getCandidate(candidateId.value),
  { server: false },
)

const viewState = computed(() =>
  resolveCandidateDetailViewState({
    pending: pending.value,
    error: error.value,
    detail: data.value,
    requestedCandidateId: candidateId.value,
  }),
)

const presentation = computed(() => {
  if (viewState.value !== 'success' || data.value == null) {
    return null
  }

  return toCandidateDetailPresentation(data.value)
})

const implementedCandidateDetailSections = [
  { id: 'candidate-overview', label: 'Overview' },
  { id: 'candidate-evidence-context', label: 'Evidence & Context' },
] as const
</script>

<template>
  <section class="page-section candidate-detail" aria-labelledby="candidate-title">
    <NuxtLink to="/candidates" class="back-link">Back to Candidate Pool</NuxtLink>

    <template v-if="viewState === 'loading'">
      <p class="eyebrow">Candidate</p>
      <h1 id="candidate-title">Candidate</h1>
      <p class="candidate-detail-message" role="status">Loading candidate details.</p>
    </template>

    <template v-else-if="viewState === 'not-found'">
      <h1 id="candidate-title">Candidate was not found.</h1>
      <p class="page-introduction">The requested Candidate does not exist.</p>
    </template>

    <template v-else-if="viewState === 'invalid-identifier'">
      <h1 id="candidate-title">The Candidate identifier is invalid.</h1>
      <p class="page-introduction">The requested Candidate identifier is not a valid Candidate ID.</p>
    </template>

    <template v-else-if="viewState === 'error'">
      <h1 id="candidate-title">Candidate details could not be loaded.</h1>
      <p class="page-introduction">Candidate details could not be loaded. Try again later.</p>
    </template>

    <template v-else-if="presentation">
      <nav class="candidate-section-nav" aria-label="Candidate sections">
        <ul class="candidate-section-nav-list">
          <li v-for="section in implementedCandidateDetailSections" :key="section.id">
            <a class="candidate-section-nav-link" :href="`#${section.id}`">{{ section.label }}</a>
          </li>
        </ul>
      </nav>

      <section
        id="candidate-overview"
        class="candidate-detail-region"
        aria-labelledby="candidate-overview-heading"
      >
        <p id="candidate-overview-heading" class="candidate-region-heading">Overview</p>

        <header class="candidate-summary">
          <p class="eyebrow">Candidate</p>
          <h1 id="candidate-title">{{ presentation.candidate.hypothesis }}</h1>
          <p class="candidate-identifier">
            <span class="candidate-id-label">Candidate ID</span>
            {{ presentation.candidate.candidateId }}
          </p>
          <p class="candidate-summary-note">
            This is a Candidate, not validated TechnicalDebt.
          </p>

          <dl class="candidate-summary-facts">
            <div>
              <dt>Affected asset</dt>
              <dd>
                <span class="candidate-asset-name">{{ presentation.candidate.assetDisplayName }}</span>
                <span class="badge badge--neutral">{{
                  candidatePoolAssetTypeLabels[presentation.candidate.canonicalAssetType]
                }}</span>
                <span class="candidate-identifier">{{ presentation.candidate.canonicalAssetKey }}</span>
              </dd>
            </div>
            <div>
              <dt>Asset criticality</dt>
              <dd>
                <span class="badge badge--neutral">{{
                  candidateAssetCriticalityLabels[presentation.enterpriseContext.asset.criticality]
                }}</span>
              </dd>
            </div>
            <div>
              <dt>Asset lifecycle status</dt>
              <dd>
                <span class="badge badge--neutral">{{
                  candidateAssetLifecycleStatusLabels[presentation.enterpriseContext.asset.lifecycleStatus]
                }}</span>
              </dd>
            </div>
          </dl>
        </header>

        <section class="candidate-detail-section" aria-labelledby="candidate-correlation-heading">
          <h2 id="candidate-correlation-heading">Correlation rationale</h2>
          <p class="candidate-section-introduction">
            System-generated deterministic correlation context. This is not validation.
          </p>
          <p class="candidate-correlation-rationale">{{ presentation.candidate.correlationRationale }}</p>
        </section>
      </section>

      <section
        id="candidate-evidence-context"
        class="candidate-detail-region"
        aria-labelledby="candidate-evidence-context-heading"
      >
        <h2 id="candidate-evidence-context-heading" class="candidate-region-heading">
          Evidence &amp; Context
        </h2>

        <div class="layout-columns candidate-detail-columns">
          <CandidateEvidenceList :evidence="presentation.evidence" />
          <CandidateSignalList :signals="presentation.signals" />
        </div>

        <CandidateEnterpriseContext
          :asset="presentation.enterpriseContext.asset"
          :ownerships="presentation.enterpriseContext.ownerships"
          :relationships="presentation.enterpriseContext.relationships"
          :incidents="presentation.enterpriseContext.incidents"
        />
        <CandidateDependencyContext :dependencyContext="presentation.dependencyContext" />
      </section>
    </template>
  </section>
</template>
