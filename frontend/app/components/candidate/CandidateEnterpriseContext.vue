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

defineProps<{
  asset: CandidateEnterpriseAssetContext
  ownerships: CandidateEnterpriseOwnershipItem[]
  relationships: CandidateDirectRelationshipItem[]
  incidents: CandidateDirectIncidentItem[]
}>()
</script>

<template>
  <section class="candidate-detail-section" aria-labelledby="candidate-enterprise-heading">
    <h2 id="candidate-enterprise-heading">Enterprise context</h2>

    <div class="candidate-context-grid">
      <section class="candidate-context-panel" aria-labelledby="candidate-asset-facts-heading">
        <h3 id="candidate-asset-facts-heading">Asset facts</h3>
        <dl class="candidate-detail-list">
          <div>
            <dt>Asset name</dt>
            <dd class="candidate-fact-primary">{{ asset.name }}</dd>
          </div>
          <div>
            <dt>Asset key</dt>
            <dd class="candidate-identifier candidate-breakable">{{ asset.assetKey }}</dd>
          </div>
          <div>
            <dt>Asset type</dt>
            <dd>
              <span class="badge badge--neutral">{{ candidatePoolAssetTypeLabels[asset.assetType] }}</span>
            </dd>
          </div>
          <div>
            <dt>Asset criticality</dt>
            <dd>
              <span class="badge badge--neutral">{{
                candidateAssetCriticalityLabels[asset.criticality]
              }}</span>
            </dd>
          </div>
          <div>
            <dt>Asset lifecycle status</dt>
            <dd>
              <span class="badge badge--neutral">{{
                candidateAssetLifecycleStatusLabels[asset.lifecycleStatus]
              }}</span>
            </dd>
          </div>
        </dl>
      </section>

      <section class="candidate-context-panel" aria-labelledby="candidate-ownership-heading">
        <h3 id="candidate-ownership-heading">Enterprise asset ownership</h3>
        <p class="candidate-section-introduction">
          These records describe ownership of the enterprise asset, not validated TechnicalDebt ownership.
        </p>
        <p v-if="ownerships.length === 0" class="candidate-section-introduction">
          No enterprise ownership records are available.
        </p>
        <ul v-else class="candidate-membership-list candidate-membership-list--cards">
          <li
            v-for="ownership in ownerships"
            :key="`${ownership.teamKey}:${ownership.ownershipRole}`"
          >
            <dl class="candidate-detail-list">
              <div>
                <dt>Team name</dt>
                <dd class="candidate-fact-primary">{{ ownership.teamName }}</dd>
              </div>
              <div>
                <dt>Ownership role</dt>
                <dd>
                  <span class="badge badge--neutral">{{
                    candidateOwnershipRoleLabels[ownership.ownershipRole]
                  }}</span>
                </dd>
              </div>
              <div>
                <dt>Team key</dt>
                <dd class="candidate-identifier candidate-breakable">{{ ownership.teamKey }}</dd>
              </div>
            </dl>
          </li>
        </ul>
      </section>

      <section class="candidate-context-panel" aria-labelledby="candidate-relationships-heading">
        <h3 id="candidate-relationships-heading">Direct relationships</h3>
        <p class="candidate-section-introduction">
          Relationships describe recorded enterprise structure; they do not establish Candidate causality.
        </p>
        <p v-if="relationships.length === 0" class="candidate-section-introduction">
          No direct relationships are recorded.
        </p>
        <ul v-else class="candidate-membership-list candidate-membership-list--cards">
          <li
            v-for="relationship in relationships"
            :key="`${relationship.sourceAssetKey}:${relationship.relationshipType}:${relationship.targetAssetKey}`"
          >
            <dl class="candidate-detail-list">
              <div>
                <dt>Relationship type</dt>
                <dd class="candidate-fact-primary">{{
                  candidateRelationshipTypeLabels[relationship.relationshipType]
                }}</dd>
              </div>
              <div>
                <dt>Source asset key</dt>
                <dd class="candidate-identifier candidate-breakable">{{ relationship.sourceAssetKey }}</dd>
              </div>
              <div>
                <dt>Target asset key</dt>
                <dd class="candidate-identifier candidate-breakable">{{ relationship.targetAssetKey }}</dd>
              </div>
            </dl>
          </li>
        </ul>
      </section>

      <section class="candidate-context-panel" aria-labelledby="candidate-incidents-heading">
        <h3 id="candidate-incidents-heading">Direct incidents</h3>
        <p class="candidate-section-introduction">
          Incidents are associated operational context and do not prove that this Candidate caused them.
        </p>
        <p v-if="incidents.length === 0" class="candidate-section-introduction">
          No direct incidents are recorded.
        </p>
        <ul v-else class="candidate-membership-list candidate-membership-list--cards">
          <li v-for="incident in incidents" :key="incident.incidentKey">
            <dl class="candidate-detail-list">
              <div>
                <dt>Title</dt>
                <dd class="candidate-fact-primary">{{ incident.title }}</dd>
              </div>
              <div>
                <dt>Incident severity</dt>
                <dd>
                  <span class="badge badge--neutral">{{
                    candidateIncidentSeverityLabels[incident.severity]
                  }}</span>
                </dd>
              </div>
              <div>
                <dt>Started at</dt>
                <dd>{{ incident.startedAt }}</dd>
              </div>
              <div v-if="incident.resolvedAt != null">
                <dt>Resolved at</dt>
                <dd>{{ incident.resolvedAt }}</dd>
              </div>
              <div>
                <dt>Incident key</dt>
                <dd class="candidate-identifier candidate-breakable">{{ incident.incidentKey }}</dd>
              </div>
            </dl>
          </li>
        </ul>
      </section>
    </div>
  </section>
</template>
