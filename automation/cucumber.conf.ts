import { defineConfig } from '@cucumber/cucumber';
import { devices } from '@playwright/test';

export default defineConfig({
  paths: ['features/**/*.feature'],
  require: [
    'step_definitions/**/*.ts',
    'hooks/**/*.ts',
    'fixtures/**/*.ts'
  ],
  requireModule: ['ts-node/register'],
  format: [
    'progress',
    'html:reports/cucumber-report.html',
    'json:reports/cucumber-report.json'
  ],
  publishQuiet: true,
  dryRun: false,
  strict: false,
  parallel: 1,
  retry: 0,
  defaultTimeout: 30000,
  worldParameters: {
    browser: 'chromium',
    headless: true,
    timeout: 30000,
    baseURL: process.env.BASE_URL || 'https://gds-demo-app.vercel.app/'
  }
});
