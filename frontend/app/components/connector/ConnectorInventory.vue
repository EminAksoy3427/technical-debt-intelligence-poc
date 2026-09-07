<script setup lang="ts">
import {
  connectorStatusLabel,
  type ConnectorSummary,
} from '~/types/connector'
import {
  connectorTechnicalDetailRows,
  type AnnotatedConnector,
} from '~/utils/annotateRegisteredConnector'

defineProps<{
  connectors: AnnotatedConnector[]
}>()

function technicalRows(connector: ConnectorSummary) {
  return connectorTechnicalDetailRows(connector)
}
</script>

<template>
  <ul class="sources-inventory" aria-label="Registered connectors">
    <li
      v-for="connector in connectors"
      :key="connector.connectorId"
      class="sources-inventory-item"
    >
      <div class="sources-inventory-heading">
        <div class="sources-inventory-copy">
          <h3 class="sources-inventory-name">{{ connector.displayName }}</h3>
          <p class="sources-inventory-role">{{ connector.roleLabel }}</p>
        </div>
        <p class="sources-inventory-status">
          <span class="badge badge--neutral">{{ connectorStatusLabel(connector.status) }}</span>
        </p>
      </div>

      <p v-if="connector.capabilitySummary" class="sources-inventory-summary">
        {{ connector.capabilitySummary }}
      </p>

      <details class="candidate-disclosure">
        <summary>Technical details</summary>
        <dl class="candidate-kv-list candidate-kv-list--compact">
          <div
            v-for="row in technicalRows(connector)"
            :key="row.label"
            class="candidate-kv-row"
          >
            <dt>{{ row.label }}</dt>
            <dd class="candidate-identifier candidate-breakable">{{ row.value }}</dd>
          </div>
        </dl>
      </details>
    </li>
  </ul>
</template>
