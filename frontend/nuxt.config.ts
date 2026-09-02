export default defineNuxtConfig({
  css: ['~/assets/css/main.css'],
  devtools: { enabled: false },
  runtimeConfig: {
    public: {
      apiBaseUrl: '',
    },
  },
})
