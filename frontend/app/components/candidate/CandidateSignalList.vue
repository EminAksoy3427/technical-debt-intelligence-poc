<script setup lang="ts">
import { candidatePoolAssetTypeLabels, type CandidateSignalItem } from '~/types/candidate'

defineProps<{
  signals: CandidateSignalItem[]
}>()
</script>

<template>
  <section class="candidate-detail-section" aria-labelledby="candidate-signals-heading">
    <h2 id="candidate-signals-heading">Signals</h2>
    <p class="candidate-section-introduction">
      These Signals are correlated members of this Candidate. A Signal is not a Candidate and does not prove validity.
    </p>
    <p v-if="signals.length === 0" class="candidate-section-introduction">
      No Signals are included in this Candidate.
    </p>
    <ul v-else class="candidate-membership-list">
      <li v-for="signal in signals" :key="signal.signalId">
        <dl class="candidate-detail-list">
          <div>
            <dt>Signal ID</dt>
            <dd class="candidate-breakable">{{ signal.signalId }}</dd>
          </div>
          <div>
            <dt>Signal type</dt>
            <dd>{{ signal.signalType }}</dd>
          </div>
          <div>
            <dt>Source system</dt>
            <dd>{{ signal.sourceSystem }}</dd>
          </div>
          <div>
            <dt>Source record ID</dt>
            <dd class="candidate-breakable">{{ signal.sourceRecordId }}</dd>
          </div>
          <div>
            <dt>Affected asset key</dt>
            <dd class="candidate-breakable">{{ signal.affectedAssetKey }}</dd>
          </div>
          <div>
            <dt>Affected asset type</dt>
            <dd>{{ candidatePoolAssetTypeLabels[signal.affectedAssetType] }}</dd>
          </div>
          <div>
            <dt>Detected at</dt>
            <dd>{{ signal.detectedAt }}</dd>
          </div>
          <div v-if="signal.severity != null">
            <dt>Severity</dt>
            <dd>{{ signal.severity }}</dd>
          </div>
        </dl>
      </li>
    </ul>
  </section>
</template>
