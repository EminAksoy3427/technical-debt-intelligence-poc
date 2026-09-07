<script setup lang="ts">
import {
  candidatePoolAssetTypeLabels,
  type CandidateDependencyContextPresentation,
} from '~/types/candidate'

defineProps<{
  dependencyContext: CandidateDependencyContextPresentation
}>()
</script>

<template>
  <section class="candidate-snapshot" aria-labelledby="candidate-dependency-snapshot-heading">
    <h2 id="candidate-dependency-snapshot-heading">Dependency snapshot</h2>
    <p class="candidate-helper">Graph connectivity, not guaranteed operational impact.</p>

    <div class="candidate-kv-list">
      <div class="candidate-kv-row">
        <h3 id="candidate-snapshot-asset-heading" class="candidate-kv-label">Candidate asset</h3>
        <div class="candidate-kv-value">
          <span class="candidate-breakable">{{ dependencyContext.candidateAsset.assetKey }}</span>
          <span class="candidate-type-badge">{{
            candidatePoolAssetTypeLabels[dependencyContext.candidateAsset.assetType]
          }}</span>
        </div>
      </div>
      <CandidateDependencyAssetList
        title="Anchors"
        heading-id="candidate-snapshot-anchors-heading"
        :assets="dependencyContext.dependencyAnchors"
      />
      <CandidateDependencyAssetList
        title="Direct dependencies"
        heading-id="candidate-snapshot-dependencies-heading"
        :assets="dependencyContext.directDependencies"
      />
      <CandidateDependencyAssetList
        title="Direct dependents"
        heading-id="candidate-snapshot-dependents-heading"
        :assets="dependencyContext.directDependents"
      />
      <CandidateDependencyAssetList
        title="Reachable dependents"
        heading-id="candidate-snapshot-reachable-heading"
        :assets="dependencyContext.reachableDependents"
      />
    </div>
  </section>
</template>
