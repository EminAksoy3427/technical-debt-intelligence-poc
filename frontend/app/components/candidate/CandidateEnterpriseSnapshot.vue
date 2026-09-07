<script setup lang="ts">
import {
  candidateAssetCriticalityLabels,
  candidateAssetLifecycleStatusLabels,
  candidateOwnershipRoleLabels,
  candidatePoolAssetTypeLabels,
  type CandidateEnterpriseAssetContext,
  type CandidateEnterpriseOwnershipItem,
} from '~/types/candidate'

defineProps<{
  asset: CandidateEnterpriseAssetContext
  ownerships: CandidateEnterpriseOwnershipItem[]
}>()
</script>

<template>
  <section class="candidate-snapshot" aria-labelledby="candidate-enterprise-snapshot-heading">
    <h2 id="candidate-enterprise-snapshot-heading">Enterprise snapshot</h2>
    <dl class="candidate-kv-list">
      <div class="candidate-kv-row">
        <dt>Asset</dt>
        <dd>
          <span class="candidate-fact-primary">{{ asset.name }}</span>
        </dd>
      </div>
      <div class="candidate-kv-row">
        <dt>Type</dt>
        <dd>
          <span class="candidate-type-badge">{{ candidatePoolAssetTypeLabels[asset.assetType] }}</span>
        </dd>
      </div>
      <div class="candidate-kv-row">
        <dt>Criticality</dt>
        <dd>{{ candidateAssetCriticalityLabels[asset.criticality] }}</dd>
      </div>
      <div class="candidate-kv-row">
        <dt>Lifecycle</dt>
        <dd>{{ candidateAssetLifecycleStatusLabels[asset.lifecycleStatus] }}</dd>
      </div>
      <div class="candidate-kv-row">
        <dt>Ownership</dt>
        <dd>
          <span v-if="ownerships.length === 0" class="candidate-empty-value">None recorded.</span>
          <ul v-else class="candidate-compact-value-list">
            <li
              v-for="ownership in ownerships"
              :key="`${ownership.teamKey}:${ownership.ownershipRole}`"
            >
              <span class="candidate-fact-primary">{{ ownership.teamName }}</span>
              <span aria-hidden="true"> · </span>
              <span>{{ candidateOwnershipRoleLabels[ownership.ownershipRole] }}</span>
            </li>
          </ul>
        </dd>
      </div>
    </dl>
  </section>
</template>
