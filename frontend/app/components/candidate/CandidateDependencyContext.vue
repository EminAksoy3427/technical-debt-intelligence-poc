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
  <section class="candidate-snapshot" aria-labelledby="candidate-dependency-heading">
    <h2 id="candidate-dependency-heading">Dependencies</h2>
    <p class="candidate-helper">
      Reachability represents graph connectivity and does not imply guaranteed operational impact or outage.
    </p>

    <div class="candidate-kv-list">
      <div class="candidate-kv-row">
        <h3 id="candidate-dependency-asset-heading" class="candidate-kv-label">Candidate asset</h3>
        <div class="candidate-kv-value">
          <span class="candidate-breakable">{{ dependencyContext.candidateAsset.assetKey }}</span>
          <span class="candidate-type-badge">{{
            candidatePoolAssetTypeLabels[dependencyContext.candidateAsset.assetType]
          }}</span>
        </div>
      </div>
      <CandidateDependencyAssetList
        title="Dependency anchors"
        heading-id="candidate-dependency-anchors-heading"
        :assets="dependencyContext.dependencyAnchors"
      />
      <CandidateDependencyAssetList
        title="Direct dependencies"
        heading-id="candidate-direct-dependencies-heading"
        :assets="dependencyContext.directDependencies"
      />
      <CandidateDependencyAssetList
        title="Direct dependents"
        heading-id="candidate-direct-dependents-heading"
        :assets="dependencyContext.directDependents"
      />
      <CandidateDependencyAssetList
        title="Reachable dependents"
        heading-id="candidate-reachable-dependents-heading"
        :assets="dependencyContext.reachableDependents"
      />
    </div>
  </section>
</template>
