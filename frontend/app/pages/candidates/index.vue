<script setup lang="ts">
import type { AssetType } from '~/types/candidateApi'
import { candidatePoolAssetTypeLabels } from '~/types/candidate'
import { filterCandidates } from '~/utils/filterCandidates'
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
  const count = filteredCandidates.value.length
  const noun = count === 1 ? 'Candidate' : 'Candidates'
  return `${count} ${noun} displayed`
})
</script>

<template>
  <section class="page-section" aria-labelledby="candidates-title">
    <header class="page-header">
      <p class="eyebrow">Technical Debt Governance</p>
      <h1 id="candidates-title">Candidates</h1>
      <p class="page-introduction">
        Evidence-supported Candidates awaiting later governance validation.
      </p>
    </header>

    <div class="candidate-pool">
      <div class="candidate-pool-heading">
        <div class="candidate-pool-heading-copy">
          <h2>Candidate Pool</h2>
          <p>Deterministically correlated Candidates supported by available evidence.</p>
        </div>
        <p
          v-if="viewState === 'ready' || viewState === 'filtered-empty'"
          class="candidate-pool-result-count"
        >
          {{ displayedCandidateCountLabel }}
        </p>
      </div>

      <p class="candidate-pool-note">
        Candidates are not validated TechnicalDebt records.
      </p>

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
            <input v-model="search" type="search" placeholder="Hypothesis or asset name" />
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
        </form>

        <CandidatePoolTable
          v-if="viewState === 'ready'"
          :candidates="filteredCandidates"
        />
        <p v-else-if="viewState === 'empty'" class="candidate-pool-status" role="status">
          No Candidates are currently available.
        </p>
        <p v-else-if="viewState === 'filtered-empty'" class="candidate-pool-status" role="status">
          No Candidates match the current filters.
        </p>
      </template>
    </div>
  </section>
</template>
