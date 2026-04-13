/**
 * Wait Helpers
 * ============
 * 
 * Robust wait strategies for Playwright automation.
 * Use these instead of hardcoded sleep() for reliable tests.
 */

import { Page, Locator, expect } from '@playwright/test';

/**
 * Wait for element to be visible
 */
export async function waitForElementVisible(
  locator: Locator,
  timeout: number = 30000
): Promise<void> {
  await locator.waitFor({ state: 'visible', timeout });
}

/**
 * Wait for element to be attached to DOM
 */
export async function waitForElementAttached(
  locator: Locator,
  timeout: number = 30000
): Promise<void> {
  await locator.waitFor({ state: 'attached', timeout });
}

/**
 * Wait for element to be hidden
 */
export async function waitForElementHidden(
  locator: Locator,
  timeout: number = 30000
): Promise<void> {
  await locator.waitFor({ state: 'hidden', timeout });
}

/**
 * Wait for text to be present in element
 */
export async function waitForText(
  locator: Locator,
  text: string,
  timeout: number = 30000
): Promise<void> {
  await locator.waitFor({ state: 'visible', timeout });
  await expect(locator).toHaveText(text, { timeout });
}

/**
 * Wait for URL to match pattern
 */
export async function waitForUrl(
  page: Page,
  pattern: string | RegExp,
  timeout: number = 30000
): Promise<void> {
  await page.waitForURL(pattern, { timeout });
}

/**
 * Wait for network request to complete
 */
export async function waitForNetworkIdle(
  page: Page,
  timeout: number = 30000
): Promise<void> {
  await page.waitForLoadState('networkidle', { timeout });
}

/**
 * Wait for condition to be true (custom polling)
 */
export async function waitForCondition(
  condition: () => Promise<boolean>,
  timeout: number = 30000,
  pollingInterval: number = 500
): Promise<void> {
  const startTime = Date.now();
  while (Date.now() - startTime < timeout) {
    if (await condition()) {
      return;
    }
    await new Promise(resolve => setTimeout(resolve, pollingInterval));
  }
  throw new Error(`Condition not met within ${timeout}ms`);
}

/**
 * Wait for page to be fully loaded
 */
export async function waitForPageLoad(
  page: Page,
  timeout: number = 30000
): Promise<void> {
  await page.waitForLoadState('domcontentloaded', { timeout });
}
