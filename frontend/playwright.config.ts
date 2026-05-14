import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  expect: { timeout: 10000 },
  fullyParallel: false,
  retries: 0,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    headless: true,
  },
  projects: [
    {
      name: 'desktop',
      use: {
        channel: 'chrome',
        viewport: { width: 1280, height: 720 },
      },
    },
    {
      name: 'mobile',
      use: {
        channel: 'chrome',
        viewport: { width: 390, height: 844 },
      },
    },
  ],
  webServer: {
    command: 'echo "Using existing dev server"',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
  },
})
