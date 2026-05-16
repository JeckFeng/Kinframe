/// <reference types="node" />
const backendPort = process.env.BACKEND_PORT || '18000'
const apiProxy = process.env.KINFRAME_API_PROXY || `http://localhost:${backendPort}`
const buildDir = process.env.NUXT_BUILD_DIR || '.nuxt'
const nitroOutputDir = process.env.NITRO_OUTPUT_DIR

export default defineNuxtConfig({
  compatibilityDate: '2026-05-11',
  buildDir,
  modules: ['@nuxtjs/tailwindcss'],
  css: ['~/assets/css/main.css'],
  runtimeConfig: {
    public: {
      apiBase: '/api',
    },
  },
  nitro: {
    output: nitroOutputDir ? { dir: nitroOutputDir } : undefined,
    routeRules: {
      '/api/**': {
        proxy: `${apiProxy}/api/**`,
      },
    },
  },
  typescript: {
    strict: true,
    tsConfig: {
      compilerOptions: {
        types: ['node'],
      },
    },
  },
})
