/**
 * Locator Helpers
 * ===============
 * 
 * Helper functions for stable and maintainable locator strategies.
 * Prioritizes data-testid, role, and text-based locators over fragile CSS/XPath.
 */

import { Page, Locator } from '@playwright/test';

// Valid ARIA roles
type AriaRole = 'alert' | 'alertdialog' | 'application' | 'article' | 'banner' | 'blockquote' | 'button' | 'caption' | 'cell' | 'checkbox' | 'code' | 'columnheader' | 'combobox' | 'complementary' | 'contentinfo' | 'definition' | 'deletion' | 'dialog' | 'directory' | 'document' | 'emphasis' | 'feed' | 'figure' | 'form' | 'generic' | 'grid' | 'gridcell' | 'group' | 'heading' | 'img' | 'insertion' | 'link' | 'list' | 'listbox' | 'listitem' | 'log' | 'main' | 'marquee' | 'math' | 'meter' | 'menu' | 'menubar' | 'menuitem' | 'menuitemcheckbox' | 'menuitemradio' | 'navigation' | 'none' | 'note' | 'option' | 'paragraph' | 'progressbar' | 'radio' | 'radiogroup' | 'region' | 'row' | 'rowgroup' | 'rowheader' | 'scrollbar' | 'search' | 'searchbox' | 'separator' | 'slider' | 'spinbutton' | 'status' | 'switch' | 'tab' | 'table' | 'tablist' | 'tabpanel' | 'term' | 'textbox' | 'timer' | 'toolbar' | 'tooltip' | 'tree' | 'treegrid' | 'treeitem';

/**
 * Get locator by data-testid (preferred strategy)
 */
export function getByTestId(page: Page, testId: string): Locator {
  return page.getByTestId(testId);
}

/**
 * Get locator by role (accessible name)
 */
export function getByRole(
  page: Page,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  role: string,
  name?: string | RegExp
): Locator {
  return page.getByRole(role as AriaRole, name ? { name } : undefined);
}

/**
 * Get locator by text content
 */
export function getByText(page: Page, text: string | RegExp): Locator {
  return page.getByText(text);
}

/**
 * Get locator by label (for form inputs)
 */
export function getByLabel(page: Page, text: string | RegExp): Locator {
  return page.getByLabel(text);
}

/**
 * Get locator by placeholder (for input fields)
 */
export function getByPlaceholder(page: Page, text: string | RegExp): Locator {
  return page.getByPlaceholder(text);
}

/**
 * Get locator by alt text (for images)
 */
export function getByAltText(page: Page, text: string | RegExp): Locator {
  return page.getByAltText(text);
}

/**
 * Get locator by title attribute
 */
export function getByTitle(page: Page, text: string | RegExp): Locator {
  return page.getByTitle(text);
}

/**
 * Get locator with multiple fallback strategies
 * Tries data-testid first, then role, then text
 */
export function getLocatorWithFallback(
  page: Page,
  identifier: string,
  options?: { role?: string; text?: boolean }
): Locator {
  // Try data-testid first (most stable)
  try {
    return getByTestId(page, identifier);
  } catch {
    // Fallback to role if specified
    if (options?.role) {
      return getByRole(page, options.role, identifier);
    }
    // Fallback to text
    if (options?.text) {
      return getByText(page, identifier);
    }
    // Last resort: CSS selector (use sparingly)
    return page.locator(`[data-testid="${identifier}"]`);
  }
}

/**
 * Get all elements matching a locator
 */
export function getAllByRole(
  page: Page,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  role: string,
  name?: string | RegExp
): Locator {
  return page.getByRole(role as AriaRole, name ? { name } : undefined);
}

/**
 * Get locator for table cell
 */
export function getTableCell(
  page: Page,
  row: number,
  column: number
): Locator {
  return page.locator(`tr:nth-child(${row}) > td:nth-child(${column})`);
}
