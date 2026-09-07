<script setup lang="ts">
import {
  candidateAssetCriticalityLabels,
  candidateAssetLifecycleStatusLabels,
  candidateGovernanceStateLabels,
  candidatePoolAssetTypeLabels,
  type CandidateDetailCore,
  type CandidateEnterpriseAssetContext,
  type CandidateGovernancePresentation,
} from '~/types/candidate'
import {
  assetCriticalityChipLabel,
  candidateGovernanceBadgeClass,
  candidateGovernanceDistinctionNotice,
} from '~/utils/candidateDetailDisplay'

const props = defineProps<{
  title: string
  canonicalProblemType: string | null
  candidate: CandidateDetailCore
  asset: CandidateEnterpriseAssetContext
  governance: CandidateGovernancePresentation
}>()

const distinctionNotice = computed(() =>
  candidateGovernanceDistinctionNotice(props.governance.state),
)

const identifierRows = computed(() => {
  const rows = [{ label: 'Candidate ID', value: props.candidate.candidateId }]
  if (props.canonicalProblemType != null) {
    rows.push({ label: 'Problem family', value: props.canonicalProblemType })
  }
  return rows
})
</script>

<template>
  <header class="candidate-detail-header">
    <nav class="candidate-breadcrumb" aria-label="Breadcrumb">
      <ol>
        <li>
          <NuxtLink to="/candidates">Candidates</NuxtLink>
        </li>
        <li aria-current="page">Candidate</li>
      </ol>
    </nav>

    <h1 id="candidate-title">{{ title }}</h1>
    <p class="candidate-header-asset">{{ asset.name }}</p>

    <ul class="candidate-chip-row">
      <li>
        <span :class="candidateGovernanceBadgeClass(governance.state)">
          {{ candidateGovernanceStateLabels[governance.state] }}
        </span>
        <span class="visually-hidden">Governance {{ governance.state }}</span>
      </li>
      <li>
        <span class="badge badge--neutral">{{ candidatePoolAssetTypeLabels[asset.assetType] }}</span>
        <span class="visually-hidden">Asset type {{ asset.assetType }}</span>
      </li>
      <li>
        <span class="badge badge--neutral">{{ assetCriticalityChipLabel(asset.criticality) }}</span>
        <span class="visually-hidden">
          Asset criticality {{ candidateAssetCriticalityLabels[asset.criticality] }}
        </span>
      </li>
      <li>
        <span class="badge badge--neutral">{{
          candidateAssetLifecycleStatusLabels[asset.lifecycleStatus]
        }}</span>
        <span class="visually-hidden">
          Asset lifecycle status {{ candidateAssetLifecycleStatusLabels[asset.lifecycleStatus] }}
        </span>
      </li>
    </ul>

    <p v-if="distinctionNotice != null && governance.state !== 'VALIDATED'" class="candidate-helper">
      {{ distinctionNotice }}
    </p>

    <CandidateProvenanceDetails
      :rows="identifierRows"
      summary-label="Technical identifiers"
    />
  </header>
</template>
