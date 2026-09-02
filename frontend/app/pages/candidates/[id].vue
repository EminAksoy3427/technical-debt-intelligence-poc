<script setup lang="ts">
import { candidatePoolAssetTypeLabels } from '~/types/candidate'
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
      <p class="eyebrow">Candidate</p>
      <h1 id="candidate-title">{{ presentation.candidate.hypothesis }}</h1>
      <p class="page-introduction">
        This record is a Candidate, not validated TechnicalDebt.
      </p>

      <section class="candidate-detail-section" aria-labelledby="candidate-identity-heading">
        <h2 id="candidate-identity-heading">Candidate identity</h2>
        <dl class="candidate-detail-list">
          <div>
            <dt>Candidate ID</dt>
            <dd class="candidate-breakable">{{ presentation.candidate.candidateId }}</dd>
          </div>
          <div>
            <dt>Hypothesis</dt>
            <dd>{{ presentation.candidate.hypothesis }}</dd>
          </div>
        </dl>
      </section>

      <section class="candidate-detail-section" aria-labelledby="candidate-asset-heading">
        <h2 id="candidate-asset-heading">Affected asset</h2>
        <dl class="candidate-detail-list">
          <div>
            <dt>Asset name</dt>
            <dd>{{ presentation.candidate.assetDisplayName }}</dd>
          </div>
          <div>
            <dt>Asset key</dt>
            <dd class="candidate-breakable">{{ presentation.candidate.canonicalAssetKey }}</dd>
          </div>
          <div>
            <dt>Asset type</dt>
            <dd>{{ candidatePoolAssetTypeLabels[presentation.candidate.canonicalAssetType] }}</dd>
          </div>
        </dl>
      </section>

      <section class="candidate-detail-section" aria-labelledby="candidate-correlation-heading">
        <h2 id="candidate-correlation-heading">Correlation rationale</h2>
        <p class="candidate-section-introduction">
          System-generated deterministic correlation context. This is not validation.
        </p>
        <p class="candidate-correlation-rationale">{{ presentation.candidate.correlationRationale }}</p>
      </section>

      <CandidateSignalList :signals="presentation.signals" />
      <CandidateEvidenceList :evidence="presentation.evidence" />
    </template>
  </section>
</template>
