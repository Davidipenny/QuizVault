import { defineConfig } from 'playwright/test'


export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:8765',
    headless: true,
    trace: 'retain-on-failure',
  },
})
