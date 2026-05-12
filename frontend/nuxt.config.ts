const apiProxy = process.env.KINFRAME_API_PROXY || 'http://localhost:8000'

export default defineNuxtConfig({
  compatibilityDate: '2026-05-11',
  modules: ['@nuxtjs/tailwindcss'],
  css: ['~/assets/css/main.css'],
  runtimeConfig: {
    public: {
      apiBase: '/api',
    },
  },
  nitro: {
    routeRules: {
      '/api/**': {
        proxy: `${apiProxy}/api/**`,
      },
    },
  },
  typescript: {
    strict: true,
  },
})
