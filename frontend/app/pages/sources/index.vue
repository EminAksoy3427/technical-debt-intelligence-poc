<script setup lang="ts">
import { toConnectorSummary } from '~/utils/mapConnectorSummary'
import { resolveConnectorInventoryViewState } from '~/utils/resolveConnectorInventoryViewState'

const { getConnectors } = useConnectorApi()

const { data, pending, error } = await useAsyncData(
  'connector-inventory',
  () => getConnectors(),
  { server: false },
)

const connectors = computed(() => (data.value?.items ?? []).map(toConnectorSummary))

const viewState = computed(() =>
  resolveConnectorInventoryViewState({
    pending: pending.value,
    hasError: Boolean(error.value),
    hasListResponse: data.value != null,
    connectorCount: connectors.value.length,
  }),
)

const registeredConnectorCountLabel = computed(() => {
  const count = connectors.value.length
  const noun = count === 1 ? 'connector' : 'connectors'
  return `${count} ${noun} registered`
})
</script>

<template>
  <section class="page-section" aria-labelledby="sources-title">
    <header class="page-header">
      <p class="eyebrow">Technical Debt Governance</p>
      <h1 id="sources-title">Sources & Connectors</h1>
      <p class="page-introduction">
        These are connectors registered in the application composition registry.
        Registration is inventory and configuration state, not a live health check
        and not a successful ingestion result.
      </p>
    </header>

    <div class="candidate-pool">
      <div class="candidate-pool-heading">
        <div class="candidate-pool-heading-copy">
          <h2>Registered connectors</h2>
          <p>Application composition inventory. This page is not a live health dashboard.</p>
        </div>
        <p
          v-if="viewState === 'ready'"
          class="candidate-pool-result-count"
        >
          {{ registeredConnectorCountLabel }}
        </p>
      </div>

      <p class="candidate-pool-note">
        Registered means the connector exists in the application registry.
        It does not mean a source is currently available or that ingestion succeeded.
      </p>

      <p v-if="viewState === 'loading'" class="candidate-pool-status" role="status">
        Loading sources and connectors.
      </p>

      <p v-else-if="viewState === 'error'" class="candidate-pool-status" role="alert">
        Sources and connectors could not be loaded.
      </p>

      <p v-else-if="viewState === 'empty'" class="candidate-pool-status" role="status">
        No connectors are currently registered.
      </p>

      <ConnectorInventoryTable
        v-else-if="viewState === 'ready'"
        :connectors="connectors"
      />
    </div>
  </section>
</template>
