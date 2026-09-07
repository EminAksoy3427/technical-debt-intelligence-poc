<script setup lang="ts">
import {
  candidateAssetCriticalityLabels,
  candidateAssetLifecycleStatusLabels,
  candidateIncidentSeverityLabels,
  candidateOwnershipRoleLabels,
  candidatePoolAssetTypeLabels,
  candidateRelationshipTypeLabels,
  type CandidateDirectIncidentItem,
  type CandidateDirectRelationshipItem,
  type CandidateEnterpriseAssetContext,
  type CandidateEnterpriseOwnershipItem,
} from '~/types/candidate'
import { formatDisplayTimestamp } from '~/utils/candidateDetailDisplay'

defineProps<{
  asset: CandidateEnterpriseAssetContext
  ownerships: CandidateEnterpriseOwnershipItem[]
  relationships: CandidateDirectRelationshipItem[]
  incidents: CandidateDirectIncidentItem[]
}>()
</script>

<template>
  <section class="candidate-snapshot" aria-labelledby="candidate-enterprise-heading">
    <h2 id="candidate-enterprise-heading">Enterprise context</h2>
    <p class="candidate-helper">
      These records describe ownership of the enterprise asset, not validated TechnicalDebt ownership.
      Relationships describe recorded enterprise structure; they do not establish Candidate causality.
      Incidents are associated operational context and do not prove that this Candidate caused them.
    </p>

    <dl class="candidate-kv-list">
      <div class="candidate-kv-row">
        <dt id="candidate-asset-facts-heading">Asset</dt>
        <dd>
          <span class="candidate-fact-primary">{{ asset.name }}</span>
          <span class="candidate-identifier candidate-breakable">{{ asset.assetKey }}</span>
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
        <dd>
          <span class="visually-hidden">Asset criticality </span>
          {{ candidateAssetCriticalityLabels[asset.criticality] }}
        </dd>
      </div>
      <div class="candidate-kv-row">
        <dt>Lifecycle</dt>
        <dd>
          <span class="visually-hidden">Asset lifecycle status </span>
          {{ candidateAssetLifecycleStatusLabels[asset.lifecycleStatus] }}
        </dd>
      </div>
      <div class="candidate-kv-row">
        <dt id="candidate-ownership-heading">Enterprise asset ownership</dt>
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
              <span class="candidate-identifier candidate-breakable">{{ ownership.teamKey }}</span>
            </li>
          </ul>
        </dd>
      </div>
      <div class="candidate-kv-row">
        <dt id="candidate-relationships-heading">Direct relationships</dt>
        <dd>
          <span v-if="relationships.length === 0" class="candidate-empty-value">None recorded.</span>
          <ul v-else class="candidate-compact-value-list">
            <li
              v-for="relationship in relationships"
              :key="`${relationship.sourceAssetKey}:${relationship.relationshipType}:${relationship.targetAssetKey}`"
            >
              <span class="candidate-type-badge">{{
                candidateRelationshipTypeLabels[relationship.relationshipType]
              }}</span>
              <span class="candidate-breakable">{{ relationship.sourceAssetKey }}</span>
              <span aria-hidden="true"> → </span>
              <span class="candidate-breakable">{{ relationship.targetAssetKey }}</span>
            </li>
          </ul>
        </dd>
      </div>
      <div class="candidate-kv-row">
        <dt id="candidate-incidents-heading">Direct incidents</dt>
        <dd>
          <span v-if="incidents.length === 0" class="candidate-empty-value">None recorded.</span>
          <ul v-else class="candidate-compact-value-list">
            <li v-for="incident in incidents" :key="incident.incidentKey">
              <div>
                <span class="candidate-fact-primary">{{ incident.title }}</span>
                <span aria-hidden="true"> · </span>
                <span>Incident severity {{ candidateIncidentSeverityLabels[incident.severity] }}</span>
              </div>
              <div class="candidate-record-meta">
                <span>{{ formatDisplayTimestamp(incident.startedAt) }}</span>
                <span v-if="incident.resolvedAt != null">
                  Resolved {{ formatDisplayTimestamp(incident.resolvedAt) }}
                </span>
                <span class="candidate-identifier candidate-breakable">{{ incident.incidentKey }}</span>
              </div>
            </li>
          </ul>
        </dd>
      </div>
    </dl>
  </section>
</template>
