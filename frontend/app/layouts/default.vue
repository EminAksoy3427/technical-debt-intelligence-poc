<template>
  <div class="application-shell">
    <a class="skip-link" href="#main-content">Skip to main content</a>
    <NavigationAppNavigation />
    <main id="main-content" class="application-content" tabindex="-1">
      <slot />
    </main>
  </div>
</template>
