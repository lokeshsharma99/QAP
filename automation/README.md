# BDD+POM Automation Framework

A Behavior Driven Development (BDD) + Page Object Model (POM) automation framework using Playwright and Cucumber.

## Structure

```
automation/
├── config/              # Configuration files
│   └── env.ts          # Environment configuration
├── features/           # Gherkin feature files
│   └── example.feature
├── step_definitions/   # Step definition implementations
│   └── example.steps.ts
├── pages/              # Page Object Models
│   ├── BasePage.ts     # Base page class
│   └── HomePage.ts     # Home page object
├── hooks/              # Cucumber hooks
│   └── hooks.ts        # Before/After hooks
├── tests/              # Test runner files
├── reports/            # Test reports
└── config/             # Framework configuration
```

## Installation

```bash
cd automation
npm install
```

## Setup

Install Playwright browsers:
```bash
npx playwright install
```

## Configuration

Set environment variables:
```bash
export BASE_URL=http://localhost:3000
export HEADLESS=false  # Run tests in headed mode
export BROWSER=chromium
```

## Running Tests

```bash
# Run all tests
npm test

# Run tests in headed mode
npm run test:headed

# Run tests in debug mode
npm run test:debug

# Generate reports
npm run report
```

## Page Object Model

All page objects extend the `BasePage` class which provides common methods:
- `navigate(url)` - Navigate to a URL
- `click(locator)` - Click on an element
- `fill(locator, value)` - Fill an input field
- `getText(locator)` - Get text from an element
- `waitForVisible(locator)` - Wait for element to be visible
- `isVisible(locator)` - Check if element is visible
- `screenshot(filename)` - Take screenshot

## Writing Tests

1. Create a feature file in `features/` directory
2. Create step definitions in `step_definitions/` directory
3. Create page objects in `pages/` directory
4. Run tests using npm scripts

## Example

See `features/example.feature`, `step_definitions/example.steps.ts`, and `pages/HomePage.ts` for examples.
