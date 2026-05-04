import { Before, After, World, setWorldConstructor, IWorldOptions } from '@cucumber/cucumber';
import { Browser, BrowserContext, Page, chromium, firefox } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

// ---------------------------------------------------------------------------
// World
// ---------------------------------------------------------------------------
export class QAPWorld extends World {
  browser!: Browser;
  context!: BrowserContext;
  page!: Page;
  baseUrl: string;
  headless: boolean;
  browserName: string;

  constructor(options: IWorldOptions) {
    super(options);
    this.baseUrl = (options.parameters as Record<string, unknown>).baseUrl as string || 'https://gds-demo-app.vercel.app';
    this.headless = (options.parameters as Record<string, unknown>).headless as boolean ?? true;
    this.browserName = (options.parameters as Record<string, unknown>).browser as string || 'chromium';
  }
}

setWorldConstructor(QAPWorld);

// ---------------------------------------------------------------------------
// Lifecycle hooks
// ---------------------------------------------------------------------------
Before(async function (this: QAPWorld) {
  const launchOptions = { headless: this.headless };

  if (this.browserName === 'firefox') {
    this.browser = await firefox.launch(launchOptions);
  } else {
    this.browser = await chromium.launch(launchOptions);
  }

  this.context = await this.browser.newContext({
    baseURL: this.baseUrl,
    viewport: { width: 1280, height: 720 },
  });

  // Start tracing on every scenario — saved only on failure in the After hook.
  // This gives Detective a trace.zip for every failure without bloating disk
  // on passing runs.
  await this.context.tracing.start({ screenshots: true, snapshots: true, sources: true });

  this.page = await this.context.newPage();
});

After(async function (this: QAPWorld, scenario) {
  const failed = scenario.result?.status === 'FAILED';

  // Save trace ZIP on failure so Detective can analyse it.
  // Discard silently on pass to avoid filling disk.
  if (failed) {
    const safeTitle = (scenario.pickle.name || 'unknown')
      .replace(/[^a-zA-Z0-9-_]/g, '_')
      .slice(0, 80);
    const traceDir = path.join('test-results');
    fs.mkdirSync(traceDir, { recursive: true });
    const tracePath = path.join(traceDir, `${safeTitle}-${Date.now()}.zip`);
    await this.context.tracing.stop({ path: tracePath });
  } else {
    await this.context.tracing.stop();
  }

  // Capture screenshot on failure
  if (failed) {
    const screenshot = await this.page.screenshot({ fullPage: true });
    this.attach(screenshot, 'image/png');
  }

  await this.page.close();
  await this.context.close();
  await this.browser.close();
});
