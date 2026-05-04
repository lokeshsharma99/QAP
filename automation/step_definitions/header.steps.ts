import { Given, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';
import { QAPWorld } from '../hooks/setup';
import { HeaderPage } from '../pages/header.page';

// Extend world with headerPage
declare module '@cucumber/cucumber' {
  interface World {
    headerPage: HeaderPage;
  }
}

// ---------------------------------------------------------------------------
// Background step
// ---------------------------------------------------------------------------

Given('the user is on the home page', async function (this: QAPWorld) {
  this.headerPage = new HeaderPage(this.page, this.baseUrl);
  await this.headerPage.navigate();
});

// ---------------------------------------------------------------------------
// AC-001: Crown logo and GOV.UK name
// ---------------------------------------------------------------------------

Then('the header should contain the Crown logo and the GOV.UK name', async function (this: QAPWorld) {
  const hasLogo = await this.headerPage.hasCrownLogo();
  const hasName = await this.headerPage.hasGovUkLogoText();
  expect(hasLogo, 'Crown logo not found in header').toBe(true);
  expect(hasName, 'GOV.UK logotype text not found in header').toBe(true);
});

// ---------------------------------------------------------------------------
// AC-002: Service name
// ---------------------------------------------------------------------------

Then('the header should contain the service name {string}', async function (this: QAPWorld, serviceName: string) {
  const hasName = await this.headerPage.hasServiceName(serviceName);
  expect(hasName, `Service name "${serviceName}" not visible in header`).toBe(true);
});

// ---------------------------------------------------------------------------
// AC-003: BETA banner
// ---------------------------------------------------------------------------

Then('the BETA banner should be visible below the header', async function (this: QAPWorld) {
  const hasBanner = await this.headerPage.hasBetaBanner();
  expect(hasBanner, 'BETA banner not visible on the page').toBe(true);
});

// ---------------------------------------------------------------------------
// AC-004: Responsive header
// ---------------------------------------------------------------------------

Then(
  'the header should be readable and functional on mobile, tablet, and desktop viewports',
  async function (this: QAPWorld) {
    const viewports = [
      { label: 'mobile', width: 375, height: 667 },
      { label: 'tablet', width: 768, height: 1024 },
      { label: 'desktop', width: 1280, height: 720 },
    ];

    for (const vp of viewports) {
      const visible = await this.headerPage.isHeaderVisibleAt(vp.width, vp.height);
      expect(visible, `Header not visible at ${vp.label} (${vp.width}x${vp.height})`).toBe(true);
    }

    // Restore default viewport
    await this.page.setViewportSize({ width: 1280, height: 720 });
  }
);

// ---------------------------------------------------------------------------
// AC-005: Skip link
// ---------------------------------------------------------------------------

Then('the skip to main content link should be present at the top of the page', async function (this: QAPWorld) {
  const hasSkip = await this.headerPage.hasSkipLink();
  expect(hasSkip, '"Skip to main content" link not found').toBe(true);
});
