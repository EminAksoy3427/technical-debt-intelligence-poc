<script setup lang="ts">
import type { AssetType } from '~/types/candidateApi'
import { candidatePoolAssetTypeLabels } from '~/types/candidate'
import { areCandidateFiltersActive, filterCandidates } from '~/utils/filterCandidates'
import { toCandidateListItem } from '~/utils/mapCandidateSummary'
import { resolveCandidatePoolViewState } from '~/utils/resolveCandidatePoolViewState'

const { getCandidates } = useCandidateApi()

const { data, pending, error } = await useAsyncData(
  'candidate-pool',
  () => getCandidates(),
  { server: false },
)

const search = ref('')
const assetType = ref<AssetType | ''>('')

const candidates = computed(() => (data.value?.items ?? []).map(toCandidateListItem))

const filtersAreActive = computed(() =>
  areCandidateFiltersActive({
    search: search.value,
    assetType: assetType.value,
  }),
)

const filteredCandidates = computed(() =>
  filterCandidates(candidates.value, {
    search: search.value,
    assetType: assetType.value,
  }),
)

const viewState = computed(() =>
  resolveCandidatePoolViewState({
    pending: pending.value,
    hasError: Boolean(error.value),
    hasListResponse: data.value != null,
    candidateCount: candidates.value.length,
    filteredCount: filteredCandidates.value.length,
  }),
)

const displayedCandidateCountLabel = computed(() => {
  const filtered = filteredCandidates.value.length
  const total = candidates.value.length

  if (filtersAreActive.value) {
    return `Showing ${filtered} of ${total} Candidates`
  }

  const noun = filtered === 1 ? 'Candidate' : 'Candidates'
  return `Showing ${filtered} ${noun}`
})

function clearFilters(): void {
  search.value = ''
  assetType.value = ''
}
</script>

<template>
  <section class="page-section candidate-review-queue" aria-labelledby="candidates-title">
    <header class="page-header page-header--queue">
      <h1 id="candidates-title">Candidates</h1>
      <p class="page-introduction">
        Review correlated technical-debt Candidates before they become governed
        TechnicalDebt records.
      </p>
    </header>

    <p v-if="viewState === 'loading'" class="candidate-pool-status" role="status">
      Loading candidates.
    </p>

    <p v-else-if="viewState === 'error'" class="candidate-pool-status" role="alert">
      Candidates could not be loaded.
    </p>

    <template v-else>
      <form class="candidate-filters" @submit.prevent>
        <label class="filter-field filter-field--search">
          <span>Search candidates</span>
          <input
            v-model="search"
            type="search"
            placeholder="Hypothesis or asset name"
          />
        </label>

        <label class="filter-field">
          <span>Asset type</span>
          <select v-model="assetType">
            <option value="">All asset types</option>
            <option
              v-for="(label, type) in candidatePoolAssetTypeLabels"
              :key="type"
              :value="type"
            >
              {{ label }}
            </option>
          </select>
        </label>

        <button
          v-if="filtersAreActive"
          type="button"
          class="button button--secondary candidate-filter-reset"
          @click="clearFilters"
        >
          Reset
        </button>
      </form>

      <p
        v-if="viewState === 'ready' || viewState === 'filtered-empty'"
        class="candidate-queue-count"
      >
        {{ displayedCandidateCountLabel }}
      </p>

      <CandidatePoolTable
        v-if="viewState === 'ready'"
        :candidates="filteredCandidates"
      />
      <p v-else-if="viewState === 'empty'" class="candidate-pool-status" role="status">
        No Candidates are currently available.
      </p>
      <div
        v-else-if="viewState === 'filtered-empty'"
        class="candidate-pool-status candidate-queue-empty"
        role="status"
      >
        <p>No Candidates match the current filters.</p>
        <button type="button" class="button button--secondary" @click="clearFilters">
          Clear filters
        </button>
      </div>
    </template>
  </section>
</template>
