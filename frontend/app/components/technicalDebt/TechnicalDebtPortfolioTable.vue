<script setup lang="ts">
import { candidatePoolAssetTypeLabels } from '~/types/candidate'
import {
  technicalDebtLifecycleStatusLabels,
  type TechnicalDebtListItem,
} from '~/types/technicalDebt'

defineProps<{
  technicalDebts: TechnicalDebtListItem[]
}>()
</script>

<template>
  <div class="candidate-table-wrapper">
    <table class="candidate-table">
      <caption class="visually-hidden">Technical Debt portfolio</caption>
      <thead>
        <tr>
          <th scope="col">Candidate hypothesis</th>
          <th scope="col">Canonical asset</th>
          <th scope="col">Lifecycle status</th>
          <th scope="col">Created at</th>
          <th class="col-action" scope="col">View</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in technicalDebts" :key="item.technicalDebtId">
          <th scope="row">
            <NuxtLink :to="`/technical-debts/${item.technicalDebtId}`" class="candidate-link">
              <span class="candidate-title">{{ item.hypothesis }}</span>
              <span class="candidate-identifier">{{ item.technicalDebtId }}</span>
            </NuxtLink>
          </th>
          <td>
            <span class="candidate-asset-name">{{ item.canonicalAssetKey }}</span>
            <span class="badge badge--neutral">{{
              candidatePoolAssetTypeLabels[item.canonicalAssetType]
            }}</span>
          </td>
          <td>
            <span class="badge badge--neutral">{{
              technicalDebtLifecycleStatusLabels[item.lifecycleStatus]
            }}</span>
            <span class="candidate-identifier">{{ item.lifecycleStatus }}</span>
          </td>
          <td>{{ item.createdAt }}</td>
          <td class="col-action candidate-action-cell">
            <NuxtLink
              :to="`/technical-debts/${item.technicalDebtId}`"
              class="candidate-action-link"
            >
              <span class="visually-hidden">View Technical Debt: {{ item.hypothesis }}</span>
              <span aria-hidden="true">View</span>
            </NuxtLink>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
