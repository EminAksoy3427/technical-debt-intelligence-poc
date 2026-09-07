<script setup lang="ts">
import {
  candidateAssetTypeDisplayLabel,
  type CandidateListItem,
} from '~/types/candidate'

defineProps<{
  candidates: CandidateListItem[]
}>()
</script>

<template>
  <ul class="overview-candidate-list">
    <li v-for="candidate in candidates" :key="candidate.id" class="overview-candidate-item">
      <div class="overview-candidate-copy">
        <NuxtLink :to="`/candidates/${candidate.id}`" class="candidate-link">
          <span class="candidate-title">{{ candidate.presentationTitle }}</span>
        </NuxtLink>
        <span class="visually-hidden">Candidate ID {{ candidate.id }}</span>
        <p class="overview-candidate-asset">
          <span class="candidate-asset-name">{{ candidate.assetName }}</span>
          <span class="candidate-type-badge">{{
            candidateAssetTypeDisplayLabel(candidate.assetType)
          }}</span>
        </p>
        <p class="overview-candidate-counts">
          Signals {{ candidate.signalCount }}
          <span aria-hidden="true"> · </span>
          Evidence {{ candidate.evidenceCount }}
        </p>
      </div>
      <NuxtLink :to="`/candidates/${candidate.id}`" class="candidate-action-link">
        Open
        <span class="visually-hidden">{{ candidate.presentationTitle }}</span>
      </NuxtLink>
    </li>
  </ul>
</template>
