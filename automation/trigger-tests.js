// trigger-tests.js - Run cucumber tests programmatically
const { execSync } = require('child_process');

const baseUrl = process.env.BASE_URL || 'https://demo.nopcommerce.com';

console.log(`Running tests against: ${baseUrl}`);

try {
  const result = execSync(
    `BASE_URL=${baseUrl} ./node_modules/.bin/cucumber-js --tags @smoke`,
    {
      cwd: __dirname,
      encoding: 'utf8',
      stdio: 'inherit',
      timeout: 120000
    }
  );
  console.log(result);
} catch (error) {
  console.error('Test execution failed:', error.message);
  process.exit(1);
}