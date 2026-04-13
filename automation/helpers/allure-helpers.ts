/**
 * Allure Helpers
 * =============
 * 
 * Allure report attachment and metadata helpers for enhanced reporting.
 * Note: These helpers require @allure-report/cucumber to be installed.
 */

/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call */

// Allure types (will be available when @allure-report/cucumber is installed)
declare global {
  const allure: any;
}

/**
 * Attach a screenshot to the Allure report
 */
export function attachScreenshot(
  filePath: string,
  name: string = 'Screenshot'
): void {
  if (typeof (globalThis as any).allure !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
    (globalThis as any).allure.attachment(name, filePath, 'image/png');
  }
}

/**
 * Attach a text file to the Allure report
 */
export function attachText(
  content: string,
  name: string = 'Text Attachment'
): void {
  if (typeof (globalThis as any).allure !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
    (globalThis as any).allure.attachment(name, Buffer.from(content), 'text/plain');
  }
}

/**
 * Attach a JSON object to the Allure report
 */
export function attachJson(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any,
  name: string = 'JSON Data'
): void {
  if (typeof (globalThis as any).allure !== 'undefined') {
    const jsonString = JSON.stringify(data, null, 2);
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
    (globalThis as any).allure.attachment(name, Buffer.from(jsonString), 'application/json');
  }
}

/**
 * Add a step to the Allure report
 */
export function addStep(stepName: string): void {
  if (typeof (globalThis as any).allure !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
    (globalThis as any).allure.step(stepName);
  }
}

/**
 * Add a parameter to the Allure report
 */
export function addParameter(name: string, value: string): void {
  if (typeof (globalThis as any).allure !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
    (globalThis as any).allure.parameter(name, value);
  }
}

/**
 * Add a description to the Allure report
 */
export function addDescription(description: string): void {
  if (typeof (globalThis as any).allure !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
    (globalThis as any).allure.description(description);
  }
}

/**
 * Add a link to the Allure report
 */
export function addLink(
  url: string,
  name?: string,
  type?: string
): void {
  if (typeof (globalThis as any).allure !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
    (globalThis as any).allure.link(url, name, type);
  }
}

/**
 * Add an issue link to the Allure report
 */
export function addIssue(url: string, name?: string): void {
  if (typeof (globalThis as any).allure !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
    (globalThis as any).allure.issue(url, name);
  }
}

/**
 * Add a TMS (Test Management System) link to the Allure report
 */
export function addTms(url: string, name?: string): void {
  if (typeof (globalThis as any).allure !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
    (globalThis as any).allure.tms(url, name);
  }
}

/**
 * Set the severity of the test in Allure
 */
export function setSeverity(severity: 'blocker' | 'critical' | 'normal' | 'minor' | 'trivial'): void {
  if (typeof (globalThis as any).allure !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
    (globalThis as any).allure.severity(severity);
  }
}

/**
 * Set the epic for the test in Allure
 */
export function setEpic(epic: string): void {
  if (typeof (globalThis as any).allure !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
    (globalThis as any).allure.epic(epic);
  }
}

/**
 * Set the feature for the test in Allure
 */
export function setFeature(feature: string): void {
  if (typeof (globalThis as any).allure !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
    (globalThis as any).allure.feature(feature);
  }
}

/**
 * Set the story for the test in Allure
 */
export function setStory(story: string): void {
  if (typeof (globalThis as any).allure !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
    (globalThis as any).allure.story(story);
  }
}

/**
 * Set the tag for the test in Allure
 */
export function setTag(tag: string): void {
  if (typeof (globalThis as any).allure !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
    (globalThis as any).allure.tag(tag);
  }
}

/**
 * Add a label to the Allure report
 */
export function addLabel(name: string, value: string): void {
  if (typeof (globalThis as any).allure !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
    (globalThis as any).allure.label(name, value);
  }
}
