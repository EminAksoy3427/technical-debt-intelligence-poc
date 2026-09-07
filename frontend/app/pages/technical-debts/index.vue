<script setup lang="ts">
import { toTechnicalDebtListItem } from '~/utils/mapTechnicalDebt'
import { resolveTechnicalDebtPortfolioViewState } from '~/utils/resolveTechnicalDebtPortfolioViewState'
import { technicalDebtInventoryCountLabel } from '~/utils/technicalDebtDisplay'
import {
  technicalDebtsInventoryEmptyExplanation,
  technicalDebtsInventoryEmptyTitle,
  technicalDebtsInventoryError,
  technicalDebtsInventoryLoading,
  technicalDebtsPageDistinction,
  technicalDebtsPageIntroduction,
  technicalDebtsPageTitle,
  technicalDebtsReviewCandidatesLabel,
} from '~/utils/technicalDebtPageCopy'

const { listTechnicalDebts } = useTechnicalDebtApi()

const { data, pending, error } = await useAsyncData(
  'technical-debt-portfolio',
  () => listTechnicalDebts(),
  { server: false },
)

const technicalDebts = computed(() => (data.value?.items ?? []).map(toTechnicalDebtListItem))

const viewState = computed(() =>
  resolveTechnicalDebtPortfolioViewState({
    pending: pending.value,
    hasError: Boolean(error.value),
    hasListResponse: data.value != null,
    technicalDebtCount: technicalDebts.value.length,
  }),
)

const displayedCountLabel = computed(() =>
  technicalDebtInventoryCountLabel(technicalDebts.value.length),
)
</script>

<template>
  <section
    class="page-section technical-debt-inventory"
    aria-labelledby="technical-debts-title"
  >
    <header class="page-header page-header--queue">
      <h1 id="technical-debts-title">{{ technicalDebtsPageTitle }}</h1>
      <p class="page-introduction">{{ technicalDebtsPageIntroduction }}</p>
      <p class="technical-debt-header-note">{{ technicalDebtsPageDistinction }}</p>
    </header>

    <p v-if="viewState === 'loading'" class="technical-debt-status" role="status">
      {{ technicalDebtsInventoryLoading }}
    </p>

    <div
      v-else-if="viewState === 'error'"
      class="technical-debt-status"
      role="alert"
    >
      <p>{{ technicalDebtsInventoryError }}</p>
      <p>
        <NuxtLink to="/candidates" class="button button--secondary">
          {{ technicalDebtsReviewCandidatesLabel }}
        </NuxtLink>
      </p>
    </div>

    <div
      v-else-if="viewState === 'empty'"
      class="technical-debt-status technical-debt-empty"
      role="status"
    >
      <p>{{ technicalDebtsInventoryEmptyTitle }}</p>
      <p class="technical-debt-empty-explanation">
        {{ technicalDebtsInventoryEmptyExplanation }}
      </p>
      <p>
        <NuxtLink to="/candidates" class="button button--secondary">
          {{ technicalDebtsReviewCandidatesLabel }}
        </NuxtLink>
      </p>
    </div>

    <template v-else-if="viewState === 'ready'">
      <p class="technical-debt-result-count">{{ displayedCountLabel }}</p>
      <TechnicalDebtPortfolioTable :technicalDebts="technicalDebts" />
    </template>
  </section>
</template>
