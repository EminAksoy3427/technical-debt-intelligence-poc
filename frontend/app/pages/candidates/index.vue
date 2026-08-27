<script setup lang="ts">
import { mockCandidates } from '~/mocks/candidates'
import type { CandidateAssetType, CandidateReviewStatus } from '~/types/candidate'
import { filterCandidates } from '~/utils/filterCandidates'

const search = ref('')
const reviewStatus = ref<CandidateReviewStatus | ''>('')
const assetType = ref<CandidateAssetType | ''>('')

const filteredCandidates = computed(() =>
  filterCandidates(mockCandidates, {
    search: search.value,
    reviewStatus: reviewStatus.value,
    assetType: assetType.value,
  }),
)
</script>

<template>
  <section class="page-section" aria-labelledby="candidates-title">
    <p class="eyebrow">Technical debt governance</p>
    <h1 id="candidates-title">Candidates</h1>
    <p class="page-introduction">
      Review technical-debt candidates supported by available evidence.
    </p>

    <div class="candidate-pool">
      <div class="candidate-pool-heading">
        <h2>Candidate pool</h2>
        <p>Candidate records are awaiting governance review or need further information.</p>
      </div>

      <form class="candidate-filters" @submit.prevent>
        <label class="filter-field filter-field--search">
          <span>Search candidates</span>
          <input v-model="search" type="search" placeholder="Title or affected asset" />
        </label>

        <label class="filter-field">
          <span>Review status</span>
          <select v-model="reviewStatus">
            <option value="">All statuses</option>
            <option value="awaiting_review">Awaiting review</option>
            <option value="needs_information">Needs information</option>
          </select>
        </label>

        <label class="filter-field">
          <span>Asset type</span>
          <select v-model="assetType">
            <option value="">All asset types</option>
            <option value="application">Application</option>
            <option value="service">Service</option>
            <option value="data_store">Data store</option>
          </select>
        </label>
      </form>

      <CandidatePoolTable
        v-if="filteredCandidates.length"
        :candidates="filteredCandidates"
      />
      <p v-else class="filtered-empty-result" role="status">
        No candidates match the current filters.
      </p>
    </div>
  </section>
</template>
