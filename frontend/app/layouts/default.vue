<script setup lang="ts">
const isNavigationOpen = ref(false)
const route = useRoute()

function closeNavigation() {
  isNavigationOpen.value = false
}

function toggleNavigation() {
  isNavigationOpen.value = !isNavigationOpen.value
}

watch(
  () => route.fullPath,
  () => {
    closeNavigation()
  },
)

function handleDocumentKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && isNavigationOpen.value) {
    closeNavigation()
  }
}

onMounted(() => {
  const desktopViewport = window.matchMedia('(min-width: 64rem)')
  const closeOnDesktop = () => {
    if (desktopViewport.matches) {
      closeNavigation()
    }
  }

  document.addEventListener('keydown', handleDocumentKeydown)
  desktopViewport.addEventListener('change', closeOnDesktop)

  onUnmounted(() => {
    document.removeEventListener('keydown', handleDocumentKeydown)
    desktopViewport.removeEventListener('change', closeOnDesktop)
  })
})
</script>

<template>
  <div class="application-shell">
    <a class="skip-link" href="#main-content">Skip to main content</a>
    <div
      class="app-sidebar-backdrop"
      :class="{ 'app-sidebar-backdrop--visible': isNavigationOpen }"
      aria-hidden="true"
      @click="closeNavigation"
    />
    <NavigationAppSidebar :open="isNavigationOpen" @close="closeNavigation" />
    <div class="application-frame">
      <NavigationAppTopbar
        :navigation-open="isNavigationOpen"
        @toggle-navigation="toggleNavigation"
      />
      <main id="main-content" class="application-content" tabindex="-1">
        <slot />
      </main>
    </div>
  </div>
</template>
