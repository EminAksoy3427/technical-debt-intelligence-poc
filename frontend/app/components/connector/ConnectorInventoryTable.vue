<script setup lang="ts">
import {
  connectorAccessLabel,
  connectorStatusLabel,
  connectorTransportLabel,
  type ConnectorSummary,
} from '~/types/connector'

defineProps<{
  connectors: ConnectorSummary[]
}>()
</script>

<template>
  <div class="candidate-table-wrapper">
    <table class="candidate-table connector-inventory-table">
      <caption class="visually-hidden">Sources & Connectors</caption>
      <thead>
        <tr>
          <th scope="col">Connector</th>
          <th scope="col">Source system</th>
          <th scope="col">Transport</th>
          <th scope="col">Access</th>
          <th scope="col">Registration</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="connector in connectors" :key="connector.connectorId">
          <th scope="row">
            <span class="candidate-title">{{ connector.displayName }}</span>
            <span class="candidate-identifier">{{ connector.connectorId }}</span>
          </th>
          <td>
            <span class="candidate-asset-name">{{ connector.sourceSystem }}</span>
          </td>
          <td>{{ connectorTransportLabel(connector.transport) }}</td>
          <td>
            <span class="badge badge--neutral">{{ connectorAccessLabel(connector.readOnly) }}</span>
          </td>
          <td>
            <span class="badge badge--info">{{ connectorStatusLabel(connector.status) }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
