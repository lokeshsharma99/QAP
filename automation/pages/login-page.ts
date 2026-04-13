import { Page } from "@playwright/test";

export class LoginPage {
  constructor(private page: Page) {}

  async navigate(): Promise<void> {
    await this.page.goto("/login");
  }

  async enterUsername(username: string): Promise<void> {
    await this.page.fill('input[name="username"]', username);
  }

  async enterPassword(password: string): Promise<void> {
    await this.page.fill('input[name="password"]', password);
  }

  async clickLoginButton(): Promise<void> {
    await this.page.click('button[type="submit"]');
  }

  async isLoggedIn(): Promise<boolean> {
    const isLoggedIn = await this.page.isVisible('[data-testid="user-profile"]');
    return isLoggedIn;
  }
}
