import { Page, Locator, expect } from '@playwright/test';

/**
 * Page Object Model for Universal Credit Personal Details Form
 * Follows Playwright best practices with role-based locators and auto-waiting
 */
export class UniversalCreditPersonalDetailsPage {
  readonly page: Page;
  
  // Locators using role-based strategies (no fragile CSS/XPath)
  readonly firstNameInput: Locator;
  readonly lastNameInput: Locator;
  readonly dateOfBirthDayInput: Locator;
  readonly dateOfBirthMonthInput: Locator;
  readonly dateOfBirthYearInput: Locator;
  readonly nationalInsuranceNumberInput: Locator;
  readonly continueButton: Locator;

  constructor(page: Page) {
    this.page = page;
    
    // Role-based locators for accessibility and stability
    this.firstNameInput = page.getByRole('textbox', { name: /first name/i });
    this.lastNameInput = page.getByRole('textbox', { name: /last name/i });
    this.dateOfBirthDayInput = page.getByRole('spinbutton', { name: /day/i });
    this.dateOfBirthMonthInput = page.getByRole('spinbutton', { name: /month/i });
    this.dateOfBirthYearInput = page.getByRole('spinbutton', { name: /year/i });
    this.nationalInsuranceNumberInput = page.getByRole('textbox', { name: /national insurance/i });
    this.continueButton = page.getByRole('button', { name: /continue/i });
  }

  /**
   * Navigate to the Universal Credit personal details page
   */
  async navigate(): Promise<void> {
    await this.page.goto('/apply-for-universal-credit/personal-details');
  }

  /**
   * Fill in the personal details form
   * Uses auto-waiting - no hardcoded sleeps
   */
  async fillPersonalDetails(data: {
    firstName: string;
    lastName: string;
    dobDay: string;
    dobMonth: string;
    dobYear: string;
    niNumber: string;
  }): Promise<void> {
    await this.firstNameInput.fill(data.firstName);
    await this.lastNameInput.fill(data.lastName);
    await this.dateOfBirthDayInput.fill(data.dobDay);
    await this.dateOfBirthMonthInput.fill(data.dobMonth);
    await this.dateOfBirthYearInput.fill(data.dobYear);
    await this.nationalInsuranceNumberInput.fill(data.niNumber);
  }

  /**
   * Click the continue button
   * Uses auto-waiting - no hardcoded sleeps
   */
  async clickContinue(): Promise<void> {
    await this.continueButton.click();
  }

  /**
   * Submit the form and wait for navigation
   */
  async submitForm(data: {
    firstName: string;
    lastName: string;
    dobDay: string;
    dobMonth: string;
    dobYear: string;
    niNumber: string;
  }): Promise<void> {
    await this.fillPersonalDetails(data);
    await this.clickContinue();
    // Auto-wait for navigation - no hardcoded waitForTimeout
    await this.page.waitForURL(/.*\/apply-for-universal-credit\/.*/);
  }

  /**
   * Verify error message is displayed
   */
  async verifyErrorMessage(message: string): Promise<void> {
    const errorElement = this.page.getByText(message);
    await expect(errorElement).toBeVisible();
  }

  /**
   * Verify field is highlighted with error
   */
  async verifyFieldError(fieldName: string): Promise<void> {
    const field = this.page.getByRole('textbox', { name: new RegExp(fieldName, 'i') });
    await expect(field).toHaveAttribute('aria-invalid', 'true');
  }
}
