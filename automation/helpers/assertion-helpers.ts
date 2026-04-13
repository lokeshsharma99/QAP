/**
 * Assertion Helpers
 * ================
 * 
 * Custom assertion wrappers for better error messages
 * and common assertion patterns.
 */

import { expect } from '@playwright/test';

/**
 * Assert element is visible with custom error message
 */
export async function assertElementVisible(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  element: any,
  message?: string
): Promise<void> {
  try {
    await expect(element).toBeVisible();
  } catch (error) {
    const errorMessage = message || 'Element is not visible';
    throw new Error(errorMessage + ': ' + String(error));
  }
}

/**
 * Assert element is enabled with custom error message
 */
export async function assertElementEnabled(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  element: any,
  message?: string
): Promise<void> {
  try {
    await expect(element).toBeEnabled();
  } catch (error) {
    const errorMessage = message || 'Element is not enabled';
    throw new Error(errorMessage + ': ' + String(error));
  }
}

/**
 * Assert text content with custom error message
 */
export async function assertTextContent(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  element: any,
  expectedText: string,
  message?: string
): Promise<void> {
  try {
    await expect(element).toHaveText(expectedText);
  } catch (error) {
    const errorMessage = message || 'Expected text "' + expectedText + '" not found';
    throw new Error(errorMessage + ': ' + String(error));
  }
}

/**
 * Assert element contains text with custom error message
 */
export async function assertContainsText(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  element: any,
  expectedText: string,
  message?: string
): Promise<void> {
  try {
    await expect(element).toContainText(expectedText);
  } catch (error) {
    const errorMessage = message || 'Expected to contain "' + expectedText + '"';
    throw new Error(errorMessage + ': ' + String(error));
  }
}

/**
 * Assert URL matches pattern with custom error message
 */
export async function assertUrlMatches(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  page: any,
  pattern: string | RegExp,
  message?: string
): Promise<void> {
  try {
    await expect(page).toHaveURL(pattern);
  } catch (error) {
    const errorMessage = message || 'URL does not match pattern ' + String(pattern);
    throw new Error(errorMessage + ': ' + String(error));
  }
}

/**
 * Assert element count with custom error message
 */
export async function assertElementCount(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  elements: any,
  expectedCount: number,
  message?: string
): Promise<void> {
  try {
    await expect(elements).toHaveCount(expectedCount);
  } catch (error) {
    const errorMessage = message || 'Expected ' + expectedCount + ' elements';
    throw new Error(errorMessage + ': ' + String(error));
  }
}
