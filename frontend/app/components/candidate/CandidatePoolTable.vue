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
  <div class="candidate-table-wrapper candidate-table-wrapper--queue">
    <table class="candidate-table candidate-table--queue">
      <caption class="visually-hidden">Candidates</caption>
      <thead>
        <tr>
          <th scope="col">Candidate</th>
          <th scope="col">Affected asset</th>
          <th class="col-count" scope="col">Signals</th>
          <th class="col-count" scope="col">Evidence</th>
          <th class="col-action" scope="col">Action</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="candidate in candidates" :key="candidate.id">
          <th scope="row">
            <NuxtLink :to="`/candidates/${candidate.id}`" class="candidate-link">
              <span class="candidate-title">{{ candidate.presentationTitle }}</span>
            </NuxtLink>
            <span class="visually-hidden">Candidate ID {{ candidate.id }}</span>
          </th>
          <td data-label="Affected asset">
            <span class="candidate-asset-line">
              <span class="candidate-asset-name">{{ candidate.assetName }}</span>
              <span class="candidate-type-badge">{{
                candidateAssetTypeDisplayLabel(candidate.assetType)
              }}</span>
            </span>
            <span class="visually-hidden">Asset type {{ candidate.assetType }}</span>
          </td>
          <td class="col-count candidate-count-cell" data-label="Signals">
            <span class="candidate-queue-metric">
              <span class="candidate-queue-metric-label">Signals</span>
              <span class="candidate-queue-metric-value">{{ candidate.signalCount }}</span>
            </span>
          </td>
          <td class="col-count candidate-count-cell" data-label="Evidence">
            <span class="candidate-queue-metric">
              <span class="candidate-queue-metric-label">Evidence</span>
              <span class="candidate-queue-metric-value">{{ candidate.evidenceCount }}</span>
            </span>
          </td>
          <td class="col-action candidate-action-cell" data-label="Action">
            <NuxtLink
              :to="`/candidates/${candidate.id}`"
              class="candidate-action-link"
            >
              Open Candidate
              <span class="visually-hidden">{{ candidate.presentationTitle }}</span>
            </NuxtLink>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
