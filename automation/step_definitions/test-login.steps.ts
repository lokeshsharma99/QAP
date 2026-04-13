import { Given, When, Then } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { LoginPage } from "../pages/login-page";

Given("the user is on the login page", async function () {
  const loginPage = new LoginPage(this.page);
  await loginPage.navigate();
});

When("the user enters username {string}", async function (username: string) {
  const loginPage = new LoginPage(this.page);
  await loginPage.enterUsername(username);
});

When("the user enters password {string}", async function (password: string) {
  const loginPage = new LoginPage(this.page);
  await loginPage.enterPassword(password);
});

When("the user clicks the login button", async function () {
  const loginPage = new LoginPage(this.page);
  await loginPage.clickLoginButton();
});

Then("the user should be logged in successfully", async function () {
  const loginPage = new LoginPage(this.page);
  const isLoggedIn = await loginPage.isLoggedIn();
  expect(isLoggedIn).toBeTruthy();
});
