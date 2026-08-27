<script setup lang="ts">
import type { CandidateListItem } from '~/types/candidate'

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
          <th scope="col">Review status</th>
          <th scope="col">Suggested team</th>
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
            <span class="candidate-asset-type">{{ candidate.assetType.replace('_', ' ') }}</span>
          </td>
          <td><CandidateStatusBadge :status="candidate.reviewStatus" /></td>
          <td>{{ candidate.suggestedTeam }}</td>
          <td><span class="count-value">{{ candidate.contributingSignalCount }}</span></td>
          <td><span class="count-value">{{ candidate.evidenceItemCount }}</span></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
