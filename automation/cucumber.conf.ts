import { IConfiguration } from '@cucumber/cucumber';

const config: Partial<IConfiguration> = {
  requireModule: ['ts-node/register'],
  require: [
    'hooks/**/*.ts',
    'step_definitions/**/*.ts',
  ],
  paths: ['features/**/*.feature'],
  format: [
    'progress-bar',
    'json:reports/cucumber-report.json',
  ],
  formatOptions: {
    snippetInterface: 'async-await',
  },
  worldParameters: {
    baseUrl: process.env.BASE_URL || 'https://lokeshsharma99.github.io/GDS-Demo-App/',
    headless: process.env.HEADLESS !== 'false',
    browser: process.env.BROWSER || 'chromium',
  },
};

export default config;
