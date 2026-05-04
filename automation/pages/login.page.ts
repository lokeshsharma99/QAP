import { Page } from '@playwright/test';
import { BasePage } from './base.page';

/**
 * LoginPage — Page Object for the authentication flow.
 *
 * Locator priority: data-testid > role > text > placeholder.
 * No hardcoded waits — relies on Playwright auto-waiting.
 */
export class LoginPage extends BasePage {
  // ---------------------------------------------------------------------------
  // Locators (data-testid first, then accessible role/text fallbacks)
  // ---------------------------------------------------------------------------
  private readonly emailInput    = () => this.byTestId('login-email').or(this.byPlaceholder('Email')).or(this.byLabel('Email'));
  private readonly passwordInput = () => this.byTestId('login-password').or(this.byPlaceholder('Password')).or(this.byLabel('Password'));
  private readonly submitButton  = () => this.byTestId('login-submit').or(this.byRole('button', { name: /sign in|log in|login/i }));
  private readonly logoutButton  = () => this.byTestId('logout-btn').or(this.byRole('button', { name: /sign out|log out|logout/i }));
  private readonly errorMessage  = () => this.byTestId('login-error').or(this.byRole('alert'));

  constructor(page: Page, baseUrl: string = '') {
    super(page, baseUrl);
  }

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------
  async navigate(): Promise<void> {
    await this.page.goto(`${this.baseUrl}/login`);
    await this.waitForLoad();
  }

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------
  async login(email: string, password: string): Promise<void> {
    await this.emailInput().fill(email);
    await this.passwordInput().fill(password);
    await this.submitButton().click();
    await this.waitForLoad();
  }

  async logout(): Promise<void> {
    await this.logoutButton().click();
    await this.waitForLoad();
  }

  // ---------------------------------------------------------------------------
  // State queries
  // ---------------------------------------------------------------------------
  async isLoggedIn(): Promise<boolean> {
    // Detect logged-in state: absence of login form OR presence of logout button
    const logoutVisible = await this.logoutButton().isVisible().catch(() => false);
    const loginFormVisible = await this.emailInput().isVisible().catch(() => false);
    return logoutVisible || !loginFormVisible;
  }

  async getErrorMessage(): Promise<string> {
    const el = this.errorMessage();
    if (await el.isVisible().catch(() => false)) {
      return (await el.textContent()) ?? '';
    }
    return '';
  }

  async isOnLoginPage(): Promise<boolean> {
    const url = await this.getCurrentUrl();
    return url.includes('/login');
  }
}
