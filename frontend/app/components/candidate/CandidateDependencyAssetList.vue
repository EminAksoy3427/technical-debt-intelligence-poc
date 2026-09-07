<script setup lang="ts">
import {
  candidatePoolAssetTypeLabels,
  type CandidateDependencyAssetItem,
} from '~/types/candidate'

defineProps<{
  title: string
  headingId: string
  assets: CandidateDependencyAssetItem[]
  headingLevel?: 'h3' | 'h4'
}>()
</script>

<template>
  <div class="candidate-kv-row">
    <component :is="headingLevel ?? 'h3'" :id="headingId" class="candidate-kv-label">
      {{ title }}
    </component>
    <div class="candidate-kv-value">
      <span v-if="assets.length === 0" class="candidate-empty-value">None recorded.</span>
      <ul v-else class="candidate-compact-value-list">
        <li v-for="asset in assets" :key="`${asset.assetType}:${asset.assetKey}`">
          <span class="candidate-breakable">{{ asset.assetKey }}</span>
          <span class="candidate-type-badge">{{ candidatePoolAssetTypeLabels[asset.assetType] }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>
