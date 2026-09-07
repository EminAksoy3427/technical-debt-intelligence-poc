<script setup lang="ts">
import { toCandidateDetailPresentation } from '~/utils/mapCandidateDetail'
import {
  parseCandidateDetailTab,
  type CandidateDetailTabId,
} from '~/utils/candidateDetailTabs'
import { resolveCandidateDetailViewState } from '~/utils/resolveCandidateDetailViewState'
import { resolveCandidatePresentationTitle } from '~/utils/resolveCandidatePresentationTitle'

const route = useRoute()
const router = useRouter()
const { getCandidate } = useCandidateApi()

const candidateId = computed(() => String(route.params.id ?? ''))
const selectedTab = computed(() => parseCandidateDetailTab(route.query.tab))

const { data, pending, error, refresh } = await useAsyncData(
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

const presentationTitle = computed(() => {
  if (presentation.value == null) {
    return null
  }

  return resolveCandidatePresentationTitle({
    hypothesis: presentation.value.candidate.hypothesis,
    signalTypes: presentation.value.signals.map((signal) => signal.signalType),
  })
})

function selectTab(tab: CandidateDetailTabId): void {
  if (tab === selectedTab.value && typeof route.query.tab === 'string') {
    return
  }

  router.replace({
    query: {
      ...route.query,
      tab,
    },
  })
}
</script>

<template>
  <section class="page-section candidate-detail" aria-labelledby="candidate-title">
    <template v-if="viewState === 'loading'">
      <nav class="candidate-breadcrumb" aria-label="Breadcrumb">
        <ol>
          <li>
            <NuxtLink to="/candidates">Candidates</NuxtLink>
          </li>
          <li aria-current="page">Candidate</li>
        </ol>
      </nav>
      <h1 id="candidate-title">Candidate</h1>
      <p class="candidate-detail-message" role="status">Loading candidate details.</p>
    </template>

    <template v-else-if="viewState === 'not-found'">
      <nav class="candidate-breadcrumb" aria-label="Breadcrumb">
        <ol>
          <li>
            <NuxtLink to="/candidates">Candidates</NuxtLink>
          </li>
          <li aria-current="page">Candidate</li>
        </ol>
      </nav>
      <h1 id="candidate-title">Candidate was not found.</h1>
      <p class="page-introduction">The requested Candidate does not exist.</p>
      <p class="candidate-detail-actions">
        <NuxtLink to="/candidates" class="button button--secondary">
          Back to Candidates
        </NuxtLink>
      </p>
    </template>

    <template v-else-if="viewState === 'invalid-identifier'">
      <nav class="candidate-breadcrumb" aria-label="Breadcrumb">
        <ol>
          <li>
            <NuxtLink to="/candidates">Candidates</NuxtLink>
          </li>
          <li aria-current="page">Candidate</li>
        </ol>
      </nav>
      <h1 id="candidate-title">The Candidate identifier is invalid.</h1>
      <p class="page-introduction">The requested Candidate identifier is not a valid Candidate ID.</p>
      <p class="candidate-detail-actions">
        <NuxtLink to="/candidates" class="button button--secondary">
          Back to Candidates
        </NuxtLink>
      </p>
    </template>

    <template v-else-if="viewState === 'error'">
      <nav class="candidate-breadcrumb" aria-label="Breadcrumb">
        <ol>
          <li>
            <NuxtLink to="/candidates">Candidates</NuxtLink>
          </li>
          <li aria-current="page">Candidate</li>
        </ol>
      </nav>
      <h1 id="candidate-title">Candidate details could not be loaded.</h1>
      <p class="page-introduction">Candidate details could not be loaded. Try again later.</p>
      <p class="candidate-detail-actions">
        <NuxtLink to="/candidates" class="button button--secondary">
          Back to Candidates
        </NuxtLink>
      </p>
    </template>

    <template v-else-if="presentation && presentationTitle">
      <CandidateDetailHeader
        :title="presentationTitle.title"
        :canonical-problem-type="presentationTitle.canonicalProblemType"
        :candidate="presentation.candidate"
        :asset="presentation.enterpriseContext.asset"
        :governance="presentation.governance"
      />

      <CandidateDetailTabs :selected-tab="selectedTab" @select="selectTab" />

      <div
        id="candidate-overview"
        class="candidate-detail-panel"
        role="tabpanel"
        aria-labelledby="candidate-tab-overview"
        :hidden="selectedTab !== 'overview'"
      >
        <CandidateOverviewTab
          :presentation="presentation"
          :problem-label="presentationTitle.title"
          @select-investigation="selectTab('investigation')"
        />
      </div>

      <div
        id="candidate-evidence-context"
        class="candidate-detail-panel"
        role="tabpanel"
        aria-labelledby="candidate-tab-evidence"
        :hidden="selectedTab !== 'evidence'"
      >
        <CandidateEvidenceContextTab :presentation="presentation" />
      </div>

      <CandidateAgentInvestigation
        :candidateId="presentation.candidate.candidateId"
        :evidence="presentation.evidence"
        :isActive="selectedTab === 'investigation'"
      />
      <CandidateHumanValidation
        :candidateId="presentation.candidate.candidateId"
        :candidateTitle="presentationTitle.title"
        :evidenceCount="presentation.evidence.length"
        :governance="presentation.governance"
        :refreshCandidate="refresh"
        :isActive="selectedTab === 'validation'"
      />
    </template>
  </section>
</template>
