<script setup lang="ts">
import { annotateRegisteredConnector } from '~/utils/annotateRegisteredConnector'
import { toConnectorSummary } from '~/utils/mapConnectorSummary'
import { resolveConnectorInventoryViewState } from '~/utils/resolveConnectorInventoryViewState'
import {
  sourcesArchitectureDistinctionHeading,
  sourcesArchitectureDistinctionNote,
  sourcesPageIntroduction,
  sourcesPageTitle,
  sourcesRegisteredConnectorsEmpty,
  sourcesRegisteredConnectorsError,
  sourcesRegisteredConnectorsHeading,
  sourcesRegisteredConnectorsLoading,
  sourcesRegisteredConnectorsNote,
  sourcesRegistrationHelper,
} from '~/utils/sourcesPageCopy'

const { getConnectors } = useConnectorApi()

const { data, pending, error } = await useAsyncData(
  'connector-inventory',
  () => getConnectors(),
  { server: false },
)

const connectors = computed(() =>
  (data.value?.items ?? []).map(toConnectorSummary).map(annotateRegisteredConnector),
)

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
  <section class="page-section sources-page" aria-labelledby="sources-title">
    <header class="page-header page-header--queue">
      <h1 id="sources-title">{{ sourcesPageTitle }}</h1>
      <p class="page-introduction">{{ sourcesPageIntroduction }}</p>
      <p class="sources-header-note">{{ sourcesRegistrationHelper }}</p>
    </header>

    <section class="sources-section" aria-labelledby="sources-distinction-heading">
      <header class="sources-section-header">
        <h2 id="sources-distinction-heading">{{ sourcesArchitectureDistinctionHeading }}</h2>
        <p class="sources-section-note">{{ sourcesArchitectureDistinctionNote }}</p>
      </header>
    </section>

    <section class="sources-section" aria-labelledby="sources-connectors-heading">
      <header class="sources-section-header sources-section-header--split">
        <div>
          <h2 id="sources-connectors-heading">{{ sourcesRegisteredConnectorsHeading }}</h2>
          <p class="sources-section-note">{{ sourcesRegisteredConnectorsNote }}</p>
        </div>
        <p
          v-if="viewState === 'ready'"
          class="sources-result-count"
        >
          {{ registeredConnectorCountLabel }}
        </p>
      </header>

      <p v-if="viewState === 'loading'" class="sources-inline-status" role="status">
        {{ sourcesRegisteredConnectorsLoading }}
      </p>

      <p v-else-if="viewState === 'error'" class="sources-inline-status" role="alert">
        {{ sourcesRegisteredConnectorsError }}
      </p>

      <p v-else-if="viewState === 'empty'" class="sources-inline-status" role="status">
        {{ sourcesRegisteredConnectorsEmpty }}
      </p>

      <ConnectorInventory
        v-else-if="viewState === 'ready'"
        :connectors="connectors"
      />
    </section>

    <SourcesSignalIngestion />
    <SourcesIngestionPipeline />
    <SourcesArchitectureNotes />
  </section>
</template>
