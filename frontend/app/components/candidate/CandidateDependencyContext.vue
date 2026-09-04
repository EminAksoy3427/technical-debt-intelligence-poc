<script setup lang="ts">
import {
  candidatePoolAssetTypeLabels,
  type CandidateDependencyAssetItem,
  type CandidateDependencyContextPresentation,
} from '~/types/candidate'

defineProps<{
  dependencyContext: CandidateDependencyContextPresentation
}>()

function assetItemKey(asset: CandidateDependencyAssetItem): string {
  return `${asset.assetType}:${asset.assetKey}`
}
</script>

<template>
  <section class="candidate-detail-section" aria-labelledby="candidate-dependency-heading">
    <h3 id="candidate-dependency-heading">Dependency context</h3>
    <p class="candidate-section-introduction">
      Deterministic dependency reachability facts. This is not guaranteed impact.
    </p>

    <section class="candidate-detail-subsection" aria-labelledby="candidate-dependency-asset-heading">
      <h4 id="candidate-dependency-asset-heading">Candidate asset</h4>
      <dl class="candidate-detail-list candidate-detail-list--inline">
        <div>
          <dt>Asset key</dt>
          <dd class="candidate-fact-primary candidate-breakable">{{
            dependencyContext.candidateAsset.assetKey
          }}</dd>
        </div>
        <div>
          <dt>Asset type</dt>
          <dd>
            <span class="badge badge--neutral">{{
              candidatePoolAssetTypeLabels[dependencyContext.candidateAsset.assetType]
            }}</span>
          </dd>
        </div>
      </dl>
    </section>

    <div class="candidate-context-grid">
      <section class="candidate-context-panel" aria-labelledby="candidate-dependency-anchors-heading">
        <h4 id="candidate-dependency-anchors-heading">
          Dependency anchors
          <span class="candidate-count-label">({{ dependencyContext.dependencyAnchors.length }})</span>
        </h4>
        <p v-if="dependencyContext.dependencyAnchors.length === 0" class="candidate-section-introduction">
          No dependency anchors are recorded.
        </p>
        <ul v-else class="candidate-membership-list candidate-membership-list--cards">
          <li v-for="asset in dependencyContext.dependencyAnchors" :key="assetItemKey(asset)">
            <dl class="candidate-detail-list candidate-detail-list--inline">
              <div>
                <dt>Asset key</dt>
                <dd class="candidate-fact-primary candidate-breakable">{{ asset.assetKey }}</dd>
              </div>
              <div>
                <dt>Asset type</dt>
                <dd>
                  <span class="badge badge--neutral">{{
                    candidatePoolAssetTypeLabels[asset.assetType]
                  }}</span>
                </dd>
              </div>
            </dl>
          </li>
        </ul>
      </section>

      <section class="candidate-context-panel" aria-labelledby="candidate-direct-dependencies-heading">
        <h4 id="candidate-direct-dependencies-heading">
          Direct dependencies
          <span class="candidate-count-label">({{ dependencyContext.directDependencies.length }})</span>
        </h4>
        <p v-if="dependencyContext.directDependencies.length === 0" class="candidate-section-introduction">
          No direct dependencies are recorded.
        </p>
        <ul v-else class="candidate-membership-list candidate-membership-list--cards">
          <li v-for="asset in dependencyContext.directDependencies" :key="assetItemKey(asset)">
            <dl class="candidate-detail-list candidate-detail-list--inline">
              <div>
                <dt>Asset key</dt>
                <dd class="candidate-fact-primary candidate-breakable">{{ asset.assetKey }}</dd>
              </div>
              <div>
                <dt>Asset type</dt>
                <dd>
                  <span class="badge badge--neutral">{{
                    candidatePoolAssetTypeLabels[asset.assetType]
                  }}</span>
                </dd>
              </div>
            </dl>
          </li>
        </ul>
      </section>

      <section class="candidate-context-panel" aria-labelledby="candidate-direct-dependents-heading">
        <h4 id="candidate-direct-dependents-heading">
          Direct dependents
          <span class="candidate-count-label">({{ dependencyContext.directDependents.length }})</span>
        </h4>
        <p v-if="dependencyContext.directDependents.length === 0" class="candidate-section-introduction">
          No direct dependents are recorded.
        </p>
        <ul v-else class="candidate-membership-list candidate-membership-list--cards">
          <li v-for="asset in dependencyContext.directDependents" :key="assetItemKey(asset)">
            <dl class="candidate-detail-list candidate-detail-list--inline">
              <div>
                <dt>Asset key</dt>
                <dd class="candidate-fact-primary candidate-breakable">{{ asset.assetKey }}</dd>
              </div>
              <div>
                <dt>Asset type</dt>
                <dd>
                  <span class="badge badge--neutral">{{
                    candidatePoolAssetTypeLabels[asset.assetType]
                  }}</span>
                </dd>
              </div>
            </dl>
          </li>
        </ul>
      </section>

      <section class="candidate-context-panel" aria-labelledby="candidate-reachable-dependents-heading">
        <h4 id="candidate-reachable-dependents-heading">
          Reachable dependents
          <span class="candidate-count-label">({{ dependencyContext.reachableDependents.length }})</span>
        </h4>
        <p class="candidate-section-introduction">
          Reachability represents graph connectivity and does not imply guaranteed operational impact or outage.
        </p>
        <p v-if="dependencyContext.reachableDependents.length === 0" class="candidate-section-introduction">
          No reachable dependents are recorded.
        </p>
        <ul v-else class="candidate-membership-list candidate-membership-list--cards">
          <li v-for="asset in dependencyContext.reachableDependents" :key="assetItemKey(asset)">
            <dl class="candidate-detail-list candidate-detail-list--inline">
              <div>
                <dt>Asset key</dt>
                <dd class="candidate-fact-primary candidate-breakable">{{ asset.assetKey }}</dd>
              </div>
              <div>
                <dt>Asset type</dt>
                <dd>
                  <span class="badge badge--neutral">{{
                    candidatePoolAssetTypeLabels[asset.assetType]
                  }}</span>
                </dd>
              </div>
            </dl>
          </li>
        </ul>
      </section>
    </div>
  </section>
</template>
