<script setup lang="ts">
import { candidateAssetTypeDisplayLabel } from '~/types/candidate'
import { formatDisplayTimestamp } from '~/utils/candidateDetailDisplay'
import {
  displayRecordedValue,
  technicalDebtLifecycleStatusDisplayLabel,
  technicalDebtPresentationTitle,
} from '~/utils/technicalDebtDisplay'
import type { TechnicalDebtDetailPresentation } from '~/types/technicalDebt'

const props = defineProps<{
  presentation: TechnicalDebtDetailPresentation
}>()

const title = computed(() =>
  technicalDebtPresentationTitle(props.presentation.sourceCandidate.hypothesis),
)

const identifierRows = computed(() => [
  { label: 'TechnicalDebt ID', value: props.presentation.technicalDebtId },
  {
    label: 'Lifecycle status',
    value: `${technicalDebtLifecycleStatusDisplayLabel(props.presentation.lifecycleStatus)} (${props.presentation.lifecycleStatus})`,
  },
  { label: 'Created at (raw)', value: props.presentation.createdAt },
  { label: 'Source Candidate ID', value: props.presentation.sourceCandidate.candidateId },
])
</script>

<template>
  <header class="candidate-detail-header">
    <nav class="candidate-breadcrumb" aria-label="Breadcrumb">
      <ol>
        <li>
          <NuxtLink to="/technical-debts">Technical Debts</NuxtLink>
        </li>
        <li aria-current="page">TechnicalDebt</li>
      </ol>
    </nav>

    <h1 id="technical-debt-title">{{ title }}</h1>
    <p class="candidate-header-asset">
      {{ displayRecordedValue(presentation.sourceCandidate.canonicalAssetKey) }}
      <span class="candidate-type-badge">{{
        candidateAssetTypeDisplayLabel(presentation.sourceCandidate.canonicalAssetType)
      }}</span>
    </p>
    <p class="candidate-helper">
      Created
      <time :datetime="presentation.createdAt">{{
        formatDisplayTimestamp(presentation.createdAt)
      }}</time>
    </p>
    <span class="visually-hidden">
      Asset type {{ presentation.sourceCandidate.canonicalAssetType }}
    </span>

    <CandidateProvenanceDetails
      :rows="identifierRows"
      summary-label="Technical identifiers"
    />
  </header>
</template>
