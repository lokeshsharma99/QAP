import { devices } from '@playwright/test';

export default {
  paths: ['features/**/*.feature'],
  require: [
    'step_definitions/**/*.ts',
    'hooks/**/*.ts',
    'fixtures/**/*.ts'
  ],
  requireModule: ['ts-node/register'],
  format: [
    'progress',
    '@allure-report/cucumber',
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
