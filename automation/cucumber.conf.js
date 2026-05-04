// cucumber.conf.js — CommonJS config loaded by Cucumber.js v11
// .ts extension is not in cucumber's loadFile allowlist; .js is.
// requireModule: ['ts-node/register'] loads TypeScript step definitions.
module.exports = {
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
