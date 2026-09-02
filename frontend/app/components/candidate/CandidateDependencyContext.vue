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
  <section class="candidate-detail-section" aria-labelledby="candidate-dependency-heading">
    <h2 id="candidate-dependency-heading">Dependency context</h2>
    <p class="candidate-section-introduction">
      Deterministic dependency reachability facts. This is not guaranteed impact.
    </p>

    <section class="candidate-detail-subsection" aria-labelledby="candidate-dependency-anchors-heading">
      <h3 id="candidate-dependency-anchors-heading">Dependency anchors</h3>
      <p v-if="dependencyContext.dependencyAnchors.length === 0" class="candidate-section-introduction">
        No dependency anchors are recorded.
      </p>
      <ul v-else class="candidate-membership-list">
        <li v-for="asset in dependencyContext.dependencyAnchors" :key="asset.assetKey">
          <dl class="candidate-detail-list">
            <div>
              <dt>Asset key</dt>
              <dd class="candidate-breakable">{{ asset.assetKey }}</dd>
            </div>
            <div>
              <dt>Asset type</dt>
              <dd>{{ candidatePoolAssetTypeLabels[asset.assetType] }}</dd>
            </div>
          </dl>
        </li>
      </ul>
    </section>

    <section class="candidate-detail-subsection" aria-labelledby="candidate-direct-dependencies-heading">
      <h3 id="candidate-direct-dependencies-heading">Direct dependencies</h3>
      <p v-if="dependencyContext.directDependencies.length === 0" class="candidate-section-introduction">
        No direct dependencies are recorded.
      </p>
      <ul v-else class="candidate-membership-list">
        <li v-for="asset in dependencyContext.directDependencies" :key="asset.assetKey">
          <dl class="candidate-detail-list">
            <div>
              <dt>Asset key</dt>
              <dd class="candidate-breakable">{{ asset.assetKey }}</dd>
            </div>
            <div>
              <dt>Asset type</dt>
              <dd>{{ candidatePoolAssetTypeLabels[asset.assetType] }}</dd>
            </div>
          </dl>
        </li>
      </ul>
    </section>

    <section class="candidate-detail-subsection" aria-labelledby="candidate-direct-dependents-heading">
      <h3 id="candidate-direct-dependents-heading">Direct dependents</h3>
      <p v-if="dependencyContext.directDependents.length === 0" class="candidate-section-introduction">
        No direct dependents are recorded.
      </p>
      <ul v-else class="candidate-membership-list">
        <li v-for="asset in dependencyContext.directDependents" :key="asset.assetKey">
          <dl class="candidate-detail-list">
            <div>
              <dt>Asset key</dt>
              <dd class="candidate-breakable">{{ asset.assetKey }}</dd>
            </div>
            <div>
              <dt>Asset type</dt>
              <dd>{{ candidatePoolAssetTypeLabels[asset.assetType] }}</dd>
            </div>
          </dl>
        </li>
      </ul>
    </section>

    <section class="candidate-detail-subsection" aria-labelledby="candidate-reachable-dependents-heading">
      <h3 id="candidate-reachable-dependents-heading">Reachable dependents</h3>
      <p class="candidate-section-introduction">
        Reachability represents graph connectivity and does not imply guaranteed operational impact or outage.
      </p>
      <p v-if="dependencyContext.reachableDependents.length === 0" class="candidate-section-introduction">
        No reachable dependents are recorded.
      </p>
      <ul v-else class="candidate-membership-list">
        <li v-for="asset in dependencyContext.reachableDependents" :key="asset.assetKey">
          <dl class="candidate-detail-list">
            <div>
              <dt>Asset key</dt>
              <dd class="candidate-breakable">{{ asset.assetKey }}</dd>
            </div>
            <div>
              <dt>Asset type</dt>
              <dd>{{ candidatePoolAssetTypeLabels[asset.assetType] }}</dd>
            </div>
          </dl>
        </li>
      </ul>
    </section>
  </section>
</template>
