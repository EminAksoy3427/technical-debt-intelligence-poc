<script setup lang="ts">
import { toTechnicalDebtListItem } from '~/utils/mapTechnicalDebt'
import { resolveTechnicalDebtPortfolioViewState } from '~/utils/resolveTechnicalDebtPortfolioViewState'

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

const displayedCountLabel = computed(() => {
  const count = technicalDebts.value.length
  const noun = count === 1 ? 'TechnicalDebt' : 'TechnicalDebts'
  return `${count} ${noun} displayed`
})
</script>

<template>
  <section class="page-section" aria-labelledby="technical-debts-title">
    <header class="page-header">
      <p class="eyebrow">Technical Debt Governance</p>
      <h1 id="technical-debts-title">Technical Debts</h1>
      <p class="page-introduction">
        REGISTERED TechnicalDebt records created by a human VALIDATE decision.
        This portfolio is not a remediation plan.
      </p>
    </header>

    <div class="candidate-pool">
      <div class="candidate-pool-heading">
        <div class="candidate-pool-heading-copy">
          <h2>TechnicalDebt portfolio</h2>
          <p>Validated structural issues. Candidates remain the source of evidence.</p>
        </div>
        <p
          v-if="viewState === 'ready'"
          class="candidate-pool-result-count"
        >
          {{ displayedCountLabel }}
        </p>
      </div>

      <p class="candidate-pool-note">
        TechnicalDebt is created only after Human Validation. REGISTERED is not
        approval of remediation work.
      </p>

      <p v-if="viewState === 'loading'" class="candidate-pool-status" role="status">
        Loading Technical Debts.
      </p>

      <p v-else-if="viewState === 'error'" class="candidate-pool-status" role="alert">
        Technical Debts could not be loaded.
      </p>

      <p v-else-if="viewState === 'empty'" class="candidate-pool-status" role="status">
        No validated TechnicalDebt records exist yet.
      </p>

      <TechnicalDebtPortfolioTable
        v-else-if="viewState === 'ready'"
        :technicalDebts="technicalDebts"
      />
    </div>
  </section>
</template>
