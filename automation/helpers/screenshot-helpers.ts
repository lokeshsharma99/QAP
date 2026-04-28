/**
 * Screenshot Helpers
 * ===================
 * 
 * Screenshot capture and attachment utilities for debugging
 * and report generation.
 */

import { Page, Locator } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Take a screenshot of the entire page
 */
export async function takeScreenshot(
  page: Page,
  fileName: string,
  directory: string = 'reports/screenshots'
): Promise<string> {
  const screenshotDir = path.resolve(directory);
  if (!fs.existsSync(screenshotDir)) {
    fs.mkdirSync(screenshotDir, { recursive: true });
  }

  const screenshotPath = path.join(screenshotDir, `${fileName}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });
  return screenshotPath;
}

/**
 * Take a screenshot of a specific element
 */
export async function takeElementScreenshot(
  locator: Locator,
  fileName: string,
  directory: string = 'reports/screenshots'
): Promise<string> {
  const screenshotDir = path.resolve(directory);
  if (!fs.existsSync(screenshotDir)) {
    fs.mkdirSync(screenshotDir, { recursive: true });
  }

  const screenshotPath = path.join(screenshotDir, `${fileName}.png`);
  await locator.screenshot({ path: screenshotPath });
  return screenshotPath;
}

/**
 * Take screenshot on failure
 */
export async function takeScreenshotOnFailure(
  page: Page,
  testName: string,
  directory: string = 'reports/screenshots/failures'
): Promise<string> {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const fileName = `${testName}-failure-${timestamp}`;
  return takeScreenshot(page, fileName, directory);
}

/**
 * Capture screenshot with timestamp
 */
export async function captureTimestampedScreenshot(
  page: Page,
  prefix: string,
  directory: string = 'reports/screenshots'
): Promise<string> {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const fileName = `${prefix}-${timestamp}`;
  return takeScreenshot(page, fileName, directory);
}

/**
 * Delete old screenshots (cleanup)
 */
export function cleanupOldScreenshots(
  directory: string = 'reports/screenshots',
  maxAgeHours: number = 24
): void {
  const screenshotDir = path.resolve(directory);
  if (!fs.existsSync(screenshotDir)) {
    return;
  }

  const now = Date.now();
  const maxAge = maxAgeHours * 60 * 60 * 1000;

  fs.readdirSync(screenshotDir).forEach(file => {
    const filePath = path.join(screenshotDir, file);
    const stats = fs.statSync(filePath);
    if (now - stats.mtimeMs > maxAge) {
      fs.unlinkSync(filePath);
    }
  });
}
