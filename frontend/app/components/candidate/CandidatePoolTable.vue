<script setup lang="ts">
import { candidatePoolAssetTypeLabels, type CandidateListItem } from '~/types/candidate'

defineProps<{
  candidates: CandidateListItem[]
}>()
</script>

<template>
  <div class="candidate-table-wrapper">
    <table class="candidate-table">
      <thead>
        <tr>
          <th scope="col">Candidate</th>
          <th scope="col">Affected asset</th>
          <th scope="col">Signals</th>
          <th scope="col">Evidence</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="candidate in candidates" :key="candidate.id">
          <th scope="row">
            <NuxtLink :to="`/candidates/${candidate.id}`" class="candidate-link">
              <span class="candidate-identifier">{{ candidate.id }}</span>
              <span class="candidate-title">{{ candidate.title }}</span>
            </NuxtLink>
          </th>
          <td>
            <span>{{ candidate.assetName }}</span>
            <span class="candidate-asset-type">{{ candidatePoolAssetTypeLabels[candidate.assetType] }}</span>
          </td>
          <td><span class="count-value">{{ candidate.signalCount }}</span></td>
          <td><span class="count-value">{{ candidate.evidenceCount }}</span></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
