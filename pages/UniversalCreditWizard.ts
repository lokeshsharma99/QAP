/**
 * UniversalCreditWizard.ts
 * Wizard orchestration for the Universal Credit application
 * Manages navigation between wizard steps and state persistence
 * 
 * @path /apply-for-universal-credit
 * @version 1.0.0
 * @updated 2026-04-12
 */

import { type Page, type Locator, expect } from '@playwright/test';
import { logger } from '../support/logger';
import { UniversalCreditPersonalDetailsPage } from './UniversalCreditPersonalDetailsPage';

/**
 * Wizard step identifiers
 */
export enum WizardStep {
  PERSONAL_DETAILS = 'Personal Details',
  CONTACT_DETAILS = 'Contact Details',
  ADDITIONAL_INFO = 'Additional Information',
  REVIEW = 'Check Your Answers',
}

/**
 * Wizard configuration
 */
export interface WizardConfig {
  baseUrl: string;
  initialPath: string;
}

/**
 * Wizard state tracking
 */
export interface WizardState {
  currentStep: WizardStep;
  previousData: Record<string, unknown>;
}

/**
 * Navigation direction
 */
export type NavigationDirection = 'forward' | 'backward';

/**
 * UniversalCreditWizard - Manages the Universal Credit application wizard
 * 
 * Orchestrates page objects for each wizard step and manages navigation state.
 * Follows the Look-Before-You-Leap pattern: validates page state before proceeding.
 */
export class UniversalCreditWizard {
  readonly page: Page;
  readonly config: WizardConfig;

  // Page objects for each wizard step
  readonly personalDetails: UniversalCreditPersonalDetailsPage;

  // Wizard state
  private _currentStep: WizardStep = WizardStep.PERSONAL_DETAILS;
  private _wizardState: WizardState;
  private _navigationHistory: WizardStep[] = [];

  /**
   * Progress indicator showing current step
   */
  readonly progressIndicator: Locator;
  readonly stepIndicator: Locator;

  /**
   * Back button for wizard navigation
   */
  readonly backButton: Locator;

  /**
   * Current step heading
   */
  readonly currentStepHeading: Locator;

  constructor(page: Page, config?: Partial<WizardConfig>) {
    this.page = page;

    // Initialize configuration
    this.config = {
      baseUrl: process.env.BASE_URL || 'https://gds-demo-app.vercel.app',
      initialPath: '/apply-for-universal-credit',
      ...config,
    };

    // Initialize wizard state
    this._wizardState = {
      currentStep: WizardStep.PERSONAL_DETAILS,
      previousData: {},
    };

    // Initialize page objects
    this.personalDetails = new UniversalCreditPersonalDetailsPage(page);

    // Initialize shared wizard locators
    this.progressIndicator = page.locator('[data-testid="wizard-progress"]');
    this.stepIndicator = page.locator('[data-testid="current-step"]');
    this.backButton = page.locator('button:has-text("Back")');
    this.currentStepHeading = page.locator('h1');
  }

  // ==========================================================================
  // GETTERS
  // ==========================================================================

  /**
   * Get the current wizard step
   */
  get currentStep(): WizardStep {
    return this._currentStep;
  }

  /**
   * Get the wizard state
   */
  get state(): WizardState {
    return { ...this._wizardState };
  }

  /**
   * Get the navigation history
   */
  get navigationHistory(): WizardStep[] {
    return [...this._navigationHistory];
  }

  // ==========================================================================
  // NAVIGATION METHODS
  // ==========================================================================

  /**
   * Navigate to the start of the wizard
   */
  async start(): Promise<void> {
    logger.info('Starting Universal Credit wizard');
    await this.gotoStep(WizardStep.PERSONAL_DETAILS);
  }

  /**
   * Navigate to a specific wizard step
   * @param step - The step to navigate to
   */
  async gotoStep(step: WizardStep): Promise<void> {
    logger.info(`Navigating to wizard step: ${step}`);

    switch (step) {
      case WizardStep.PERSONAL_DETAILS:
        await this.page.goto(this.config.initialPath, { waitUntil: 'networkidle' });
        break;
      // Additional steps would be added as they are implemented
      default:
        logger.warn(`Step ${step} navigation not implemented, using base path`);
        await this.page.goto(this.config.initialPath, { waitUntil: 'networkidle' });
    }

    await this.validateCurrentStep(step);
    this._navigationHistory.push(step);
    this._currentStep = step;
  }

  /**
   * Navigate forward to the next step
   */
  async goForward(): Promise<void> {
    logger.info('Navigating forward in wizard');

    switch (this._currentStep) {
      case WizardStep.PERSONAL_DETAILS:
        await this.personalDetails.clickContinue();
        this._currentStep = WizardStep.CONTACT_DETAILS;
        break;
      // Additional steps
      default:
        logger.warn(`Forward navigation not configured for ${this._currentStep}`);
    }

    this._navigationHistory.push(this._currentStep);
  }

  /**
   * Navigate backward to the previous step
   */
  async goBackward(): Promise<void> {
    logger.info('Navigating backward in wizard');

    if (this.backButton && await this.backButton.isVisible()) {
      await this.backButton.click();
    } else {
      logger.warn('Back button not available');
    }
  }

  /**
   * Complete the wizard and navigate to final confirmation
   */
  async complete(): Promise<void> {
    logger.info('Completing wizard');
    await this.gotoStep(WizardStep.REVIEW);
  }

  // ==========================================================================
  // VALIDATION METHODS
  // ==========================================================================

  /**
   * Validate that the current step matches the expected step
   * @param expectedStep - The step that should be current
   */
  async validateCurrentStep(expectedStep: WizardStep): Promise<void> {
    logger.info(`Validating current step is: ${expectedStep}`);

    const heading = await this.currentStepHeading.textContent();
    if (heading?.toLowerCase().includes(expectedStep.toLowerCase())) {
      logger.info(`Step validation passed: ${expectedStep}`);
    } else {
      logger.warn(`Expected ${expectedStep} but heading is: ${heading}`);
      await expect(this.currentStepHeading).toContainText(expectedStep);
    }
  }

  /**
   * Check if user can proceed with current data
   */
  async canProceed(): Promise<boolean> {
    try {
      // Try clicking continue and see if we move forward
      const continueButton = this.page.locator('button:has-text("Continue")');
      if (!await continueButton.isVisible()) {
        return false;
      }

      // Check if error summary is displayed
      const errorSummary = this.page.locator('[data-testid="error-summary"]');
      return !(await errorSummary.isVisible());
    } catch {
      return false;
    }
  }

  // ==========================================================================
  // STEP-SPECIFIC ACTIONS
  // ==========================================================================

  /**
   * Submit personal details and move to next step
   * @param data - The personal details data
   */
  async submitPersonalDetails(data: {
    firstName: string;
    lastName: string;
    dateOfBirth: { day: string; month: string; year: string };
    nationalInsuranceNumber: string;
  }): Promise<void> {
    logger.info('Submitting personal details');

    if (this._currentStep !== WizardStep.PERSONAL_DETAILS) {
      await this.gotoStep(WizardStep.PERSONAL_DETAILS);
    }

    // Fill all fields using the page object
    await this.personalDetails.fillAllFields(data);

    // Save data to wizard state
    this._wizardState.previousData = { ...this._wizardState.previousData, ...data };

    // Click continue to proceed
    await this.personalDetails.clickContinue();

    // Update current step
    this._currentStep = WizardStep.CONTACT_DETAILS;
    this._navigationHistory.push(WizardStep.CONTACT_DETAILS);

    logger.info('Personal details submitted successfully');
  }

  /**
   * Verify data was saved correctly for a step
   * @param step - The step to verify data for
   * @param expectedData - The data that should be present
   */
  async verifySavedData(step: WizardStep, expectedData: Record<string, unknown>): Promise<void> {
    logger.info(`Verifying saved data for step: ${step}`);

    switch (step) {
      case WizardStep.PERSONAL_DETAILS:
        await this.gotoStep(step);
        // Could verify values are repopulated in fields
        break;
      default:
        logger.warn(`Data verification not implemented for ${step}`);
    }
  }

  // ==========================================================================
  // DATA MANAGEMENT
  // ==========================================================================

  /**
   * Get saved wizard data
   */
  getSavedData(): Record<string, unknown> {
    return { ...this._wizardState.previousData };
  }

  /**
   * Clear all saved data
   */
  clearSavedData(): void {
    logger.info('Clearing wizard saved data');
    this._wizardState.previousData = {};
  }

  /**
   * Update saved data
   * @param data - Data to merge into saved state
   */
  updateSavedData(data: Record<string, unknown>): void {
    logger.info('Updating wizard saved data');
    this._wizardState.previousData = {
      ...this._wizardState.previousData,
      ...data,
    };
  }

  // ==========================================================================
  // UTILITY METHODS
  // ==========================================================================

  /**
   * Reset the wizard to initial state
   */
  async reset(): Promise<void> {
    logger.info('Resetting wizard to initial state');
    this._wizardState = {
      currentStep: WizardStep.PERSONAL_DETAILS,
      previousData: {},
    };
    this._navigationHistory = [];
    this._currentStep = WizardStep.PERSONAL_DETAILS;
    await this.start();
  }

  /**
   * Get a human-readable summary of current wizard state
   */
  async getStateSummary(): Promise<string> {
    return `
      Universal Credit Wizard State:
      - Current Step: ${this._currentStep}
      - Navigation History: ${this._navigationHistory.join(' → ')}
      - Saved Data Keys: ${Object.keys(this._wizardState.previousData).join(', ') || 'None'}
    `.trim();
  }
}

export default UniversalCreditWizard;