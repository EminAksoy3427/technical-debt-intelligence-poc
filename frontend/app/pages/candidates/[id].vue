<script setup lang="ts">
import { getMockCandidateDetail } from '~/mocks/candidateDetails'

const route = useRoute()
const candidate = computed(() => getMockCandidateDetail(String(route.params.id)))
</script>

<template>
  <section v-if="candidate" class="page-section candidate-detail" aria-labelledby="candidate-title">
    <NuxtLink to="/candidates" class="back-link">Back to Candidate Pool</NuxtLink>

    <p class="eyebrow">Candidate under review</p>
    <h1 id="candidate-title">{{ candidate.id }}: {{ candidate.title }}</h1>
    <p class="page-introduction">
      This record is a Candidate for governance review, not validated TechnicalDebt.
    </p>

    <section class="candidate-detail-section candidate-detail-status" aria-labelledby="candidate-status-heading">
      <h2 id="candidate-status-heading">Review status</h2>
      <CandidateStatusBadge :status="candidate.reviewStatus" />
    </section>

    <CandidateContext :context="candidate.context" />

    <section class="candidate-detail-section" aria-labelledby="candidate-asset-heading">
      <h2 id="candidate-asset-heading">Affected asset</h2>
      <dl class="candidate-detail-list">
        <div>
          <dt>Asset name</dt>
          <dd>{{ candidate.assetName }}</dd>
        </div>
        <div>
          <dt>Asset type</dt>
          <dd class="candidate-asset-type">{{ candidate.assetType.replace('_', ' ') }}</dd>
        </div>
      </dl>
    </section>

    <section class="candidate-detail-section" aria-labelledby="candidate-ownership-heading">
      <h2 id="candidate-ownership-heading">Suggested ownership</h2>
      <dl class="candidate-detail-list">
        <div>
          <dt>Suggested team</dt>
          <dd>{{ candidate.suggestedTeam }}</dd>
        </div>
      </dl>
      <p class="candidate-context-note">Suggested Team is proposed ownership, not a validated TechnicalDebt ownership decision.</p>
    </section>

    <CandidateEvidenceList :evidence="candidate.evidence" />
  </section>

  <section v-else class="page-section" aria-labelledby="candidate-not-found-title">
    <NuxtLink to="/candidates" class="back-link">Back to Candidate Pool</NuxtLink>
    <h1 id="candidate-not-found-title">Candidate not found.</h1>
    <p class="page-introduction">The requested Candidate does not exist in this controlled mock.</p>
  </section>
</template>
