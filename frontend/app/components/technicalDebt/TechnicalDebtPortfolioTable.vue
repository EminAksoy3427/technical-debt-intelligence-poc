<script setup lang="ts">
import { candidateAssetTypeDisplayLabel } from '~/types/candidate'
import { formatDisplayTimestamp } from '~/utils/candidateDetailDisplay'
import {
  displayRecordedValue,
  technicalDebtPresentationTitle,
} from '~/utils/technicalDebtDisplay'
import type { TechnicalDebtListItem } from '~/types/technicalDebt'

defineProps<{
  technicalDebts: TechnicalDebtListItem[]
}>()
</script>

<template>
  <div class="candidate-table-wrapper technical-debt-table-wrapper">
    <table class="candidate-table technical-debt-table">
      <caption class="visually-hidden">Governed TechnicalDebt inventory</caption>
      <thead>
        <tr>
          <th scope="col">Technical debt</th>
          <th scope="col">Source Candidate</th>
          <th scope="col">Canonical asset</th>
          <th scope="col">Created</th>
          <th class="col-action" scope="col">Action</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in technicalDebts" :key="item.technicalDebtId">
          <th scope="row">
            <NuxtLink
              :to="`/technical-debts/${item.technicalDebtId}`"
              class="candidate-link"
            >
              <span class="candidate-title">{{
                technicalDebtPresentationTitle(item.hypothesis)
              }}</span>
            </NuxtLink>
            <span class="visually-hidden">
              TechnicalDebt ID {{ item.technicalDebtId }}
            </span>
          </th>
          <td data-label="Source Candidate">
            <span class="technical-debt-cell-label">Source Candidate</span>
            <NuxtLink
              class="candidate-reference-link"
              :to="`/candidates/${item.sourceCandidateId}`"
            >
              Open Candidate
              <span class="visually-hidden">
                {{ technicalDebtPresentationTitle(item.hypothesis) }}
              </span>
            </NuxtLink>
            <span class="visually-hidden">
              Candidate ID {{ item.sourceCandidateId }}
            </span>
          </td>
          <td data-label="Canonical asset">
            <span class="technical-debt-cell-label">Canonical asset</span>
            <span class="candidate-asset-line">
              <span class="candidate-asset-name">{{
                displayRecordedValue(item.canonicalAssetKey)
              }}</span>
              <span class="candidate-type-badge">{{
                candidateAssetTypeDisplayLabel(item.canonicalAssetType)
              }}</span>
            </span>
            <span class="visually-hidden">Asset type {{ item.canonicalAssetType }}</span>
          </td>
          <td data-label="Created">
            <span class="technical-debt-cell-label">Created</span>
            <time :datetime="item.createdAt">{{
              formatDisplayTimestamp(item.createdAt)
            }}</time>
          </td>
          <td class="col-action candidate-action-cell" data-label="Action">
            <NuxtLink
              :to="`/technical-debts/${item.technicalDebtId}`"
              class="candidate-action-link"
            >
              Open TechnicalDebt
              <span class="visually-hidden">{{
                technicalDebtPresentationTitle(item.hypothesis)
              }}</span>
            </NuxtLink>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
