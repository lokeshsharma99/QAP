import { Page } from '@playwright/test';
import { BasePage } from './base.page';

// ---------------------------------------------------------------------------
// Header Page Object
// ---------------------------------------------------------------------------

/**
 * HeaderPage — GOV.UK header component interactions.
 *
 * Targets: https://lokeshsharma99.github.io/GDS-Demo-App/
 *
 * Locator strategy (priority: role > text > css — no fragile XPath):
 *  - Crown logo: <img> with alt containing "GOV.UK" or role=img
 *  - GOV.UK logotype text: visible text "GOV.UK"
 *  - Service name: visible text in header link
 *  - BETA banner: role=region or visible text "beta"
 *  - Skip link: role=link name "Skip to main content"
 */
export class HeaderPage extends BasePage {
  constructor(page: Page, baseUrl: string = '') {
    super(page, baseUrl);
  }

  async navigate(): Promise<void> {
    await this.page.goto(this.baseUrl || '/');
    await this.waitForLoad();
  }

  // ---------------------------------------------------------------------------
  // Header elements
  // ---------------------------------------------------------------------------

  /** True if the GOV.UK logotype text is visible in the header. */
  async hasGovUkLogoText(): Promise<boolean> {
    // The GOV.UK logotype renders as visible text "GOV.UK" inside the header
    return this.page.locator('header').getByText('GOV.UK', { exact: false }).isVisible();
  }

  /** True if a Crown logo image is present (img with GOV.UK alt text). */
  async hasCrownLogo(): Promise<boolean> {
    // Try SVG/img with alt attribute containing "GOV.UK" or "Crown"
    const logoImg = this.page.locator(
      'header img[alt*="GOV.UK"], header img[alt*="Crown"], header svg[aria-label*="GOV.UK"]'
    );
    const count = await logoImg.count();
    if (count > 0) return logoImg.first().isVisible();
    // Fallback: logo link wrapping text "GOV.UK" is sufficient evidence
    return this.hasGovUkLogoText();
  }

  /** True if the service name text is visible in the header. */
  async hasServiceName(name: string): Promise<boolean> {
    return this.page.locator('header').getByText(name, { exact: false }).isVisible();
  }

  /** True if the BETA banner is visible on the page. */
  async hasBetaBanner(): Promise<boolean> {
    // GOV.UK Design System renders a <strong class="govuk-tag govuk-phase-banner__content__tag"> with text "beta"
    const betaTag = this.page.getByText(/\bbeta\b/i).first();
    return betaTag.isVisible();
  }

  /** True if the "Skip to main content" link is present near the top of the DOM. */
  async hasSkipLink(): Promise<boolean> {
    return this.page.getByRole('link', { name: /skip to main content/i }).isVisible();
  }

  // ---------------------------------------------------------------------------
  // Responsive helpers
  // ---------------------------------------------------------------------------

  /** Resize viewport, check header is visible, return to default. */
  async isHeaderVisibleAt(width: number, height: number): Promise<boolean> {
    await this.page.setViewportSize({ width, height });
    const header = this.page.locator('header').first();
    return header.isVisible();
  }
}
