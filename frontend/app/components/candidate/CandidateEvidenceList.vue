<script setup lang="ts">
import type { CandidateEvidenceItem } from '~/types/candidate'

defineProps<{
  evidence: CandidateEvidenceItem[]
}>()

function httpReferenceHref(referenceUri: string): string | undefined {
  return /^https?:\/\//i.test(referenceUri) ? referenceUri : undefined
}
</script>

<template>
  <section
    class="candidate-detail-section candidate-evidence-section"
    aria-labelledby="candidate-evidence-heading"
  >
    <h3 id="candidate-evidence-heading">Evidence</h3>
    <p class="candidate-section-introduction">
      Evidence provides provenance for this Candidate. Evidence does not validate the Candidate.
    </p>
    <p v-if="evidence.length === 0" class="candidate-section-introduction">
      No Evidence is included in this Candidate.
    </p>
    <ul v-else class="candidate-membership-list candidate-membership-list--cards">
      <li v-for="item in evidence" :key="item.evidenceId" class="candidate-evidence-item">
        <dl class="candidate-detail-list candidate-detail-list--scan">
          <div class="candidate-fact-span">
            <dt>Source reference</dt>
            <dd class="candidate-fact-primary">{{ item.sourceReference }}</dd>
          </div>
          <div>
            <dt>Evidence ID</dt>
            <dd class="candidate-identifier candidate-breakable">{{ item.evidenceId }}</dd>
          </div>
          <div>
            <dt>Source system</dt>
            <dd>{{ item.sourceSystem }}</dd>
          </div>
          <div>
            <dt>Captured at</dt>
            <dd>{{ item.capturedAt }}</dd>
          </div>
          <div v-if="item.referenceUri != null" class="candidate-fact-span">
            <dt>Reference URI</dt>
            <dd>
              <a
                v-if="httpReferenceHref(item.referenceUri)"
                class="candidate-reference-link"
                :href="httpReferenceHref(item.referenceUri)"
                rel="noopener noreferrer"
                target="_blank"
              >
                {{ item.referenceUri }}
                <span class="visually-hidden">(opens in a new tab)</span>
              </a>
              <span v-else class="candidate-breakable">{{ item.referenceUri }}</span>
            </dd>
          </div>
        </dl>
      </li>
    </ul>
  </section>
</template>
