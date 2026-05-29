/**
 * Playwright config for the QA stress-test tour.
 * Hits an existing vite dev server (must already be running on PORT).
 */

import { defineConfig, devices } from '@playwright/test';

const PORT = process.env.QA_PORT || '5273';

export default defineConfig({
  testDir: './e2e',
  // Run both QA tours: the route-level screenshot tour and the in-page tab tour.
  testMatch: /qa_.*_tour\.spec\.ts/,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 120000,
  reporter: [['list']],
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: 'off',
    screenshot: 'off',
    viewport: { width: 1440, height: 900 },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // No webServer — assume vite is already running externally
});
