import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.PREVIEW_URL || 'http://localhost:3000';

export default defineConfig({
  testDir: '.',
  timeout: 60_000,
  expect: {
    timeout: 15_000,
  },
  use: {
    baseURL,
    headless: true,
    ignoreHTTPSErrors: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
