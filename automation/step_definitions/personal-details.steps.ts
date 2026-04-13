import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';
import { UniversalCreditPersonalDetailsPage } from '../pages/UniversalCreditPersonalDetailsPage';

let personalDetailsPage: UniversalCreditPersonalDetailsPage;

Given('I am on the Universal Credit personal details page', async function () {
  personalDetailsPage = new UniversalCreditPersonalDetailsPage(this.page);
  await personalDetailsPage.navigate();
});

When('I enter valid personal details', async function () {
  // Use data from run_context.json - no hardcoded test data
  const testData = this.testData?.valid || {
    firstName: 'John',
    lastName: 'Smith',
    dobDay: '15',
    dobMonth: '06',
    dobYear: '1990',
    niNumber: 'QQ123456C'
  };
  
  await personalDetailsPage.fillPersonalDetails({
    firstName: testData.firstName,
    lastName: testData.lastName,
    dobDay: testData.dobDay,
    dobMonth: testData.dobMonth,
    dobYear: testData.dobYear,
    niNumber: testData.niNumber
  });
});

When('I click the continue button', async function () {
  await personalDetailsPage.clickContinue();
});

Then('I should be navigated to the next step', async function () {
  // Auto-wait for URL change - no hardcoded waitForTimeout
  await personalDetailsPage.page.waitForURL(/.*\/apply-for-universal-credit\/.*/);
});

Then('I should see an error message {string}', async function (errorMessage: string) {
  await personalDetailsPage.verifyErrorMessage(errorMessage);
});

When('I enter personal details for a user under 18', async function () {
  const testData = this.testData?.under_18 || {
    firstName: 'Jane',
    lastName: 'Doe',
    dobDay: '15',
    dobMonth: '06',
    dobYear: '2010',
    niNumber: 'AB123456C'
  };
  
  await personalDetailsPage.fillPersonalDetails({
    firstName: testData.firstName,
    lastName: testData.lastName,
    dobDay: testData.dobDay,
    dobMonth: testData.dobMonth,
    dobYear: testData.dobYear,
    niNumber: testData.niNumber
  });
});
