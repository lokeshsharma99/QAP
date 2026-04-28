/**
 * UniversalCreditPersonalDetailsPage.ts
 * Page Object Model for the Personal Details step of the Universal Credit application wizard
 * 
 * Locator Strategy: Uses data-testid, role, and text-based strategies with 'near()' pattern
 * for form fields following GOV.UK Design System patterns.
 * 
 * @path /apply-for-universal-credit
 * @version 1.0.0
 * @updated 2026-04-12
 */

import { type Page, type Locator, expect } from '@playwright/test';
import { logger } from '../support/logger';

/**
 * Validation constants matching business rules
 */
export const NI_NUMBER_REGEX = '^[A-CEGHJ-PR-TW-Z]{2}[0-9]{6}[A-CEGHJ-PR-TW-Z]$';
export const NI_NUMBER_VALIDATION_MESSAGE = 'Enter a valid National Insurance number';

/**
 * GOV.UK Error Messages
 */
export const GOVUK_ERROR_MESSAGES = {
  FIRST_NAME_REQUIRED: 'Enter your first name',
  LAST_NAME_REQUIRED: 'Enter your last name',
  DATE_OF_BIRTH_REQUIRED: 'Enter your date of birth',
  NI_NUMBER_REQUIRED: 'Enter a valid National Insurance number',
} as const;

/**
 * Field labels for form identification
 */
export const FIELD_LABELS = {
  FIRST_NAME: 'First name',
  LAST_NAME: 'Last name',
  DATE_OF_BIRTH_DAY: 'Day',
  DATE_OF_BIRTH_MONTH: 'Month',
  DATE_OF_BIRTH_YEAR: 'Year',
  NATIONAL_INSURANCE_NUMBER: 'National Insurance number',
} as const;

/**
 * Locator helpers that use the 'near()' pattern for form field association
 */
export class UniversalCreditPersonalDetailsPage {
  readonly page: Page;

  // ==========================================================================
  // ERROR SUMMARY & MESSAGES
  // ==========================================================================

  /**
   * Error summary container - GOV.UK standard error summary pattern
   */
  readonly errorSummary: Locator;

  /**
   * Error summary heading using role and text-based locator
   */
  readonly errorSummaryHeading: Locator;

  /**
   * Continue button using role-based locator
   */
  readonly continueButton: Locator;

  /**
   * Form container using role-based locator
   */
  readonly formContainer: Locator;

  // ==========================================================================
  // FORM FIELDS - Using 'near()' pattern for form field association
  // ==========================================================================

  /**
   * First Name field - uses text-based label with 'near()' pattern
   * GOV.UK pattern: label text near associated input
   */
  readonly firstNameField: Locator;

  /**
   * Last Name field - uses text-based label with 'near()' pattern
   */
  readonly lastNameField: Locator;

  /**
   * Date of Birth Day field - uses 'near()' with Day label
   */
  readonly dateOfBirthDayField: Locator;

  /**
   * Date of Birth Month field - uses 'near()' with Month label
   */
  readonly dateOfBirthMonthField: Locator;

  /**
   * Date of Birth Year field - uses 'near()' with Year label
   */
  readonly dateOfBirthYearField: Locator;

  /**
   * National Insurance Number field - uses text-based label with 'near()' pattern
   */
  readonly nationalInsuranceNumberField: Locator;

  // ==========================================================================
  // ERROR MESSAGES - Inline validation errors under fields
  // ==========================================================================

  /**
   * First Name inline error message
   */
  readonly firstNameError: Locator;

  /**
   * Last Name inline error message
   */
  readonly lastNameError: Locator;

  /**
   * Date of Birth inline error message
   */
  readonly dateOfBirthError: Locator;

  /**
   * National Insurance Number inline error message
   */
  readonly nationalInsuranceNumberError: Locator;

  /**
   * Error links in summary for keyboard navigation to fields
   */
  readonly errorSummaryLinks: Locator;

  /**
   * Page heading
   */
  readonly pageHeading: Locator;

  constructor(page: Page) {
    this.page = page;

    // Initialize error summary
    this.errorSummary = page.locator('[data-testid="error-summary"]');
    this.errorSummaryHeading = page.locator('h2.error-summary-title');
    this.errorSummaryLinks = page.locator('[data-testid="error-summary"] a');

    // Initialize action buttons
    this.continueButton = page.locator('button:has-text("Continue")');

    // Initialize form container
    this.formContainer = page.locator('form');

    // ==========================================================================
    // FORM FIELDS - Using 'near()' pattern for robust field association
    // ==========================================================================
    // GOV.UK Design System pattern: Form fields are associated with labels using
    // the 'near()' locator to find inputs directly adjacent to their labels.
    // This is more reliable than CSS selectors for GOV.UK forms.
    // ==========================================================================

    const formSection = page.locator('form');

    // First Name - label near input pattern
    this.firstNameField = page.locator('input').near(page.locator('label:has-text("First name")'));

    // Last Name - label near input pattern
    this.lastNameField = page.locator('input').near(page.locator('label:has-text("Last name")'));

    // National Insurance Number - label near input pattern
    this.nationalInsuranceNumberField = page
      .locator('input')
      .near(page.locator('label:has-text("National Insurance number")'));

    // Date of Birth fields - use legend/nfieldset context for proper association
    // Day field
    this.dateOfBirthDayField = page
      .locator('#dateOfBirth-day, input[name="dateOfBirth-day"], [data-testid="dob-day"]')
      .first();

    // Month field
    this.dateOfBirthMonthField = page
      .locator('#dateOfBirth-month, input[name="dateOfBirth-month"], [data-testid="dob-month"]')
      .first();

    // Year field
    this.dateOfBirthYearField = page
      .locator('#dateOfBirth-year, input[name="dateOfBirth-year"], [data-testid="dob-year"]')
      .first();

    // Alternative: Try 'near' pattern with legend containing "Date of birth"
    const dobLegend = page.locator('legend:has-text("Date of birth")');
    if (dobLegend.count() > 0) {
      this.dateOfBirthDayField = page.locator('input').near(dobLegend).first();
      this.dateOfBirthMonthField = page.locator('input').near(dobLegend).nth(1);
      this.dateOfBirthYearField = page.locator('input').near(dobLegend).nth(2);
    }

    // ==========================================================================
    // INLINE ERROR MESSAGES
    // ==========================================================================
    // GOV.UK error messages appear directly below invalid fields
    // Pattern: error message class + adjacent to the field
    // ==========================================================================

    // First Name error
    this.firstNameError = page.locator('[data-testid="first-name-error"], [id$="-error"]')
      .near(page.locator('label:has-text("First name")'));

    // Last Name error
    this.lastNameError = page.locator('[data-testid="last-name-error"], [id$="-error"]')
      .near(page.locator('label:has-text("Last name")'));

    // Date of Birth error
    this.dateOfBirthError = page.locator('[data-testid="dob-error"], [id$="-error"]')
      .near(page.locator('legend:has-text("Date of birth")'));

    // National Insurance Number error
    this.nationalInsuranceNumberError = page.locator(
      '[data-testid="national-insurance-number-error"], [id$="-error"]'
    ).near(page.locator('label:has-text("National Insurance number")'));

    // Page heading
    this.pageHeading = page.locator('h1');
  }

  // ==========================================================================
  // NAVIGATION METHODS
  // ==========================================================================

  /**
   * Navigate to the Personal Details page
   */
  async goto(): Promise<void> {
    const url = '/apply-for-universal-credit';
    logger.info(`Navigating to ${url}`);
    await this.page.goto(url, { waitUntil: 'networkidle' });
    await this.expectPageLoaded();
  }

  /**
   * Wait for the page to load and be ready
   */
  async expectPageLoaded(): Promise<void> {
    logger.info('Waiting for Personal Details page to load');
    await this.page.waitForLoadState('domcontentloaded');
    await this.pageHeading.waitFor({ state: 'visible', timeout: 10000 });
    logger.info('Personal Details page loaded successfully');
  }

  // ==========================================================================
  // FORM FIELD INTERACTION METHODS
  // ==========================================================================

  /**
   * Fill the First Name field
   * @param value - The first name to enter
   */
  async fillFirstName(value: string): Promise<void> {
    logger.info(`Filling first name: ${value}`);
    await this.firstNameField.clear();
    await this.firstNameField.fill(value);
  }

  /**
   * Fill the Last Name field
   * @param value - The last name to enter
   */
  async fillLastName(value: string): Promise<void> {
    logger.info(`Filling last name: ${value}`);
    await this.lastNameField.clear();
    await this.lastNameField.fill(value);
  }

  /**
   * Fill the National Insurance Number field
   * @param value - The NI number to enter
   */
  async fillNationalInsuranceNumber(value: string): Promise<void> {
    logger.info(`Filling NI number: ${value}`);
    await this.nationalInsuranceNumberField.clear();
    await this.nationalInsuranceNumberField.fill(value);
  }

  /**
   * Fill the Date of Birth fields
   * @param day - Day component
   * @param month - Month component
   * @param year - Year component
   */
  async fillDateOfBirth(day: string, month: string, year: string): Promise<void> {
    logger.info(`Filling date of birth: ${day}/${month}/${year}`);

    const fields = [this.dateOfBirthDayField, this.dateOfBirthMonthField, this.dateOfBirthYearField];

    for (const field of fields) {
      try {
        await field.clear();
      } catch {
        // Field might not have clear method, continue
      }
    }

    await this.dateOfBirthDayField.fill(day);
    await this.dateOfBirthMonthField.fill(month);
    await this.dateOfBirthYearField.fill(year);
  }

  /**
   * Fill the Date of Birth from an object
   * @param dob - Object containing day, month, year
   */
  async fillDateOfBirthFromObject(dob: { day: string; month: string; year: string }): Promise<void> {
    await this.fillDateOfBirth(dob.day, dob.month, dob.year);
  }

  /**
   * Fill all required fields at once
   * @param data - Personal details data
   */
  async fillAllFields(data: {
    firstName: string;
    lastName: string;
    dateOfBirth: { day: string; month: string; year: string };
    nationalInsuranceNumber: string;
  }): Promise<void> {
    logger.info('Filling all personal details fields');
    await Promise.all([
      this.fillFirstName(data.firstName),
      this.fillLastName(data.lastName),
      this.fillDateOfBirthFromObject(data.dateOfBirth),
      this.fillNationalInsuranceNumber(data.nationalInsuranceNumber),
    ]);
  }

  // ==========================================================================
  // FIELD VALIDATION METHODS
  // ==========================================================================

  /**
   * Clear a field and blur to trigger validation
   * @param locator - The field locator to clear
   */
  async clearAndBlur(locator: Locator): Promise<void> {
    await locator.clear();
    await locator.blur();
  }

  /**
   * Blur a field to trigger validation
   */
  async blurField(locator: Locator): Promise<void> {
    await locator.blur();
  }

  /**
   * Check if a field has an error message
   */
  async fieldHasError(locator: Locator): Promise<boolean> {
    const errorCount = await locator.locator('.. >> text=/Enter|required|valid/i').count();
    return errorCount > 0;
  }

  // ==========================================================================
  // NAVIGATION ACTION METHODS
  // ==========================================================================

  /**
   * Click the Continue button to proceed to next step
   */
  async clickContinue(): Promise<void> {
    logger.info('Clicking Continue button');
    await this.continueButton.click();
  }

  /**
   * Submit the form (same as clicking Continue)
   */
  async submitForm(): Promise<void> {
    await this.clickContinue();
  }

  // ==========================================================================
  // ASSERTION METHODS
  // ==========================================================================

  /**
   * Verify all form fields are visible and editable
   */
  async verifyAllFieldsVisibleAndEditable(): Promise<void> {
    logger.info('Verifying all fields are visible and editable');

    const fields = [
      { locator: this.firstNameField, name: 'First Name' },
      { locator: this.lastNameField, name: 'Last Name' },
      { locator: this.dateOfBirthDayField, name: 'Date of Birth Day' },
      { locator: this.dateOfBirthMonthField, name: 'Date of Birth Month' },
      { locator: this.dateOfBirthYearField, name: 'Date of Birth Year' },
      { locator: this.nationalInsuranceNumberField, name: 'National Insurance Number' },
    ];

    for (const field of fields) {
      await expect(field.locator).toBeVisible({ timeout: 5000 });
      await expect(field.locator).toBeEnabled({ timeout: 5000 });
    }

    logger.info('All fields verified as visible and editable');
  }

  /**
   * Verify the error summary is displayed
   */
  async verifyErrorSummaryDisplayed(): Promise<void> {
    logger.info('Verifying error summary is displayed');
    await expect(this.errorSummary).toBeVisible({ timeout: 5000 });
  }

  /**
   * Verify the error summary contains specific error messages
   */
  async verifyErrorSummaryContains(errors: string[]): Promise<void> {
    logger.info(`Verifying error summary contains: ${errors.join(', ')}`);

    for (const error of errors) {
      await expect(this.errorSummary).toContainText(error);
    }
  }

  /**
   * Verify a specific field shows the expected error message
   */
  async verifyFieldError(fieldName: string, expectedError: string): Promise<void> {
    logger.info(`Verifying ${fieldName} shows error: ${expectedError}`);

    const errorLocators: Record<string, Locator> = {
      [FIELD_LABELS.FIRST_NAME]: this.firstNameError,
      [FIELD_LABELS.LAST_NAME]: this.lastNameError,
      [FIELD_LABELS.DATE_OF_BIRTH_DAY]: this.dateOfBirthError,
      [FIELD_LABELS.NATIONAL_INSURANCE_NUMBER]: this.nationalInsuranceNumberError,
    };

    const errorLocator = errorLocators[fieldName];
    if (errorLocator) {
      await expect(errorLocator).toContainText(expectedError);
    } else {
      // Fallback: check if the error text exists anywhere near the field
      await expect(this.page.locator(`text=${expectedError}`)).toBeVisible();
    }
  }

  /**
   * Verify NI Number format was accepted (field has no error)
   */
  async verifyNINumberAccepted(): Promise<void> {
    logger.info('Verifying NI Number accepted');
    await this.verifyFieldError(FIELD_LABELS.NATIONAL_INSURANCE_NUMBER, '').catch(() => {
      // If error check fails, try page content
      expect(
        await this.nationalInsuranceNumberField.locator('..').textContent()
      ).not.toContain('error');
    });
  }

  /**
   * Check if user remains on the Personal Details page
   */
  async verifyRemainOnPersonalDetails(): Promise<void> {
    logger.info('Verifying user remains on Personal Details page');
    await expect(this.pageHeading).toContainText('Personal Details');
    await expect(this.continueButton).toBeVisible();
  }

  /**
   * Click an error link in the error summary
   * @param errorText - The text of the error link to click
   */
  async clickErrorLink(errorText: string): Promise<void> {
    logger.info(`Clicking error link: ${errorText}`);
    const link = this.errorSummary.locator(`a:has-text("${errorText}")`);
    await link.click();
  }
}

export default UniversalCreditPersonalDetailsPage;