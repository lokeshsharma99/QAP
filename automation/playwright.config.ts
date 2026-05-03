import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './features',
  timeout: 30_000,
  retries: process.env.CI ? 2 : 0,
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'reports/playwright-report.json' }],
  ],
  use: {
    baseURL: process.env.BASE_URL || 'https://lokeshsharma99.github.io/GDS-Demo-App/',
    headless: process.env.HEADLESS !== 'false',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    // trace: always on so Detective always has a trace.zip to analyse on failure
    trace: 'on-first-retry',
    // Locator strategy: prefer data-testid over CSS/XPath
    testIdAttribute: 'data-testid',
  },
  // Output dir — test-results/ is picked up by Detective's parse_trace_zip tool
  outputDir: 'test-results',
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
  ],
});
