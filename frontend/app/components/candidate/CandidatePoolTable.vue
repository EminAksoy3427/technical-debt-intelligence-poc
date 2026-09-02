<script setup lang="ts">
import { candidatePoolAssetTypeLabels, type CandidateListItem } from '~/types/candidate'

defineProps<{
  candidates: CandidateListItem[]
}>()
</script>

<template>
  <div class="candidate-table-wrapper">
    <table class="candidate-table">
      <caption class="visually-hidden">Candidate Pool</caption>
      <thead>
        <tr>
          <th scope="col">Candidate</th>
          <th scope="col">Affected asset</th>
          <th class="col-count" scope="col">Signals</th>
          <th class="col-count" scope="col">Evidence</th>
          <th class="col-action" scope="col">View</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="candidate in candidates" :key="candidate.id">
          <th scope="row">
            <NuxtLink :to="`/candidates/${candidate.id}`" class="candidate-link">
              <span class="candidate-title">{{ candidate.title }}</span>
              <span class="candidate-identifier">{{ candidate.id }}</span>
            </NuxtLink>
          </th>
          <td>
            <span class="candidate-asset-name">{{ candidate.assetName }}</span>
            <span class="badge badge--neutral">{{ candidatePoolAssetTypeLabels[candidate.assetType] }}</span>
          </td>
          <td class="col-count candidate-count-cell">
            <span class="count-value">{{ candidate.signalCount }}</span>
          </td>
          <td class="col-count candidate-count-cell">
            <span class="count-value">{{ candidate.evidenceCount }}</span>
          </td>
          <td class="col-action candidate-action-cell">
            <NuxtLink
              :to="`/candidates/${candidate.id}`"
              class="candidate-action-link"
            >
              <span class="visually-hidden">View candidate: {{ candidate.title }}</span>
              <span aria-hidden="true">View</span>
            </NuxtLink>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
