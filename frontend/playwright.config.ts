import { defineConfig } from '@playwright/test'

const devPort = Number(process.env.PLAYWRIGHT_DEV_PORT || '3000')
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://localhost:${devPort}`
const skipWebServer = process.env.PLAYWRIGHT_SKIP_WEBSERVER === '1'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  expect: { timeout: 10000 },
  fullyParallel: false,
  retries: 0,
  use: {
    baseURL,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    headless: true,
  },
  projects: [
    {
      name: 'desktop',
      use: {
        browserName: 'chromium',
        viewport: { width: 1280, height: 720 },
      },
    },
    {
      name: 'mobile',
      use: {
        browserName: 'chromium',
        viewport: { width: 390, height: 844 },
      },
    },
  ],
  webServer: skipWebServer
    ? undefined
    : {
        command: `pnpm exec nuxt dev --host 0.0.0.0 --port ${devPort}`,
        url: baseURL,
        reuseExistingServer: true,
        timeout: 120000,
      },
})
