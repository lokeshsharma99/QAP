# language: en
@GDS-8 @confirmation @universal-credit @wizard-step-5
Feature: Confirmation - Universal Credit Application
  As a Universal Credit applicant
  I want to see a confirmation after submitting my application
  So that I know my application was received and I understand next steps

  Background: Common setup for Confirmation page
    Given I have successfully submitted my Universal Credit application
    And I am on the "Confirmation" page

  # =============================================================================
  # POSITIVE PATH SCENARIOS
  # =============================================================================

  @smoke @positive-path
  Scenario: Confirmation page displays unique reference number
    Then I should see a confirmation heading "Application submitted"
    And I should see a reference number displayed in the format "UC-YYYY-MM-DD-XXXX"
    And the reference number should be highlighted or prominently displayed

  @smoke @positive-path
  Scenario: Confirmation page shows next steps information
    Then I should see a "What happens next" section
    And the "What happens next" section should describe the decision timeframe
    And the "What happens next" section should mention possible follow-up contact

  @regression @positive-path
  Scenario: User can print the confirmation page
    When I click the "Print" button or link
    Then the browser print dialog should open
    And the printed page should contain my reference number

  @regression @positive-path
  Scenario: User can save the confirmation page as PDF
    When I use the browser's save as PDF function
    Then the saved PDF should contain my reference number
    And the saved PDF should contain the application summary

  # =============================================================================
  # ACCEPTANCE CRITERION: Reference number is valid and unique
  # =============================================================================

  @acceptance-criteria @GDS-8-AC-1
  Scenario: Reference number follows expected format
    When I note the reference number displayed
    Then the reference number should match the pattern "UC-YYYY-MM-DD-XXXX"
    And the year (YYYY) should be 2026 or later
    And the month (MM) should be 01-12
    And the day (DD) should be 01-31
    And the suffix (XXXX) should be a 4-digit number

  @acceptance-criteria @GDS-8-AC-2
  Scenario: Reference number is unique across multiple applications
    Given I submit a second Universal Credit application
    When I reach the confirmation page for the second application
    Then the second reference number should be different from the first reference number

  # =============================================================================
  # ACCEPTANCE CRITERION: All submitted application data is summarised
  # =============================================================================

  @acceptance-criteria @GDS-8-AC-3
  Scenario: Confirmation page shows summary of submitted application
    Then a "Your application" summary section should be displayed
    And the summary should include my personal details
    And the summary should include my contact details
    And the summary should include my additional information

  @regression @summary
  Scenario: Application summary matches data entered in wizard
    Given I entered the following in Personal Details:
      | Field       | Value              |
      | First name  | John               |
      | Last name   | Smith              |
      | NI number   | QQ123456C          |
    And I entered the following in Contact Details:
      | Field          | Value                |
      | Email          | john.smith@example.com |
      | Phone          | 07700 900123        |
    And I entered the following in Additional Information:
      | Field              | Value      |
      | Marital status     | Single     |
      | Employment status  | Employed   |
    When I view the confirmation page
    Then the application summary should show "John Smith"
    And the application summary should show "QQ123456C"
    And the application summary should show "john.smith@example.com"
    And the application summary should show "Single"
    And the application summary should show "Employed"

  # =============================================================================
  # ACCEPTANCE CRITERION: What happens next guidance is clear
  # =============================================================================

  @acceptance-criteria @GDS-8-AC-4
  Scenario: Confirmation page clearly explains next steps
    Then I should see a section titled "What happens next"
    And the "What happens next" section should mention decision timeframe
    And the "What happens next" section should mention:
      """
      We'll write to you within 5 working days to confirm we've received your application.
      We may contact you if we need more information.
      """
    And the "What happens next" section should provide a contact phone number for queries

  @regression @next-steps
  Scenario: Contact information for queries is displayed
    Then the page should display the Universal Credit helpline number
    And the page should display the expected response time

  # =============================================================================
  # ACCEPTANCE CRITERION: User cannot modify application after submission
  # =============================================================================

  @acceptance-criteria @GDS-8-AC-5
  Scenario: Wizard edit links are not available after submission
    When I view the confirmation page
    Then the "Edit" links should not be visible
    And the "Back" button should not be visible

  @acceptance-criteria @GDS-8-AC-6
  Scenario: User cannot navigate backwards after final submission
    When I try to use the browser back button
    Then I should remain on the confirmation page or be redirected to the home page

  # =============================================================================
  # ACCEPTANCE CRITERION: Application status after submission
  # =============================================================================

  @acceptance-criteria @GDS-8-AC-7
  Scenario: Application is marked as submitted in the system
    When I check the application status via alternative means
    Then my application should be recorded as "Submitted"
    And the submission timestamp should be recorded

  @regression @application-status
  Scenario: Submitted application can be retrieved by reference number
    When I note my reference number
    And I search for my application using the reference number
    Then the application should be found
    And the application status should be "Submitted"

  # =============================================================================
  # POST-SUBMISSION USER JOURNEYS
  # =============================================================================

  @regression @post-submission
  Scenario: User can log out after submission
    When I click the "Sign out" link
    Then I should be logged out
    And I should be taken to the login page or home page

  @regression @post-submission
  Scenario: User can return to confirmation page after logging in again
    Given I have logged out after submitting my application
    And I have logged back in with the same credentials
    When I navigate to "My applications"
    Then I should see my submitted Universal Credit application
    And the status should show as "Submitted"
    And the reference number should be displayed

  # =============================================================================
  # ERROR SCENARIOS - DUPLICATE SUBMISSION PROTECTION
  # =============================================================================

  @regression @error-handling
  Scenario: Prevent duplicate submission if user refreshes page after submission
    Given I have just submitted my application
    When I refresh the confirmation page
    Then I should see a message informing me the application has already been submitted
    And no duplicate application should be created in the system

  @regression @error-handling
  Scenario: Prevent duplicate submission if user uses back button to resubmit
    Given I have submitted my application
    And I try to navigate back to the Check Your Answers page
    When I attempt to submit again
    Then I should see an error message "This application has already been submitted"
    And no duplicate application should be created

  # =============================================================================
  # ACCESSIBILITY CHECKS
  # =============================================================================

  @acceptance-criteria @GDS-8-AC-8 @accessibility
  Scenario: Confirmation page is accessible
    Then the page should have a main heading "Application submitted"
    And the reference number should be within an h1 or have aria-live="polite"
    And there should be a Skip to main content link
    And the page should have correct heading hierarchy (h1 for page title, h2 for sections)
    And all images should have appropriate alt text

  @regression @accessibility
  Scenario: Success message is announced to screen readers
    When the confirmation page loads
    Then the success message should be announced via aria-live region

  # =============================================================================
  # DATA REQUIREMENTS DOCUMENTATION
  # =============================================================================

  # Test Data Patterns:
  # Reference number format: UC-YYYY-MM-DD-XXXX (e.g., UC-2026-05-01-1234)
  # Must be unique per application submission
  # Reference number should be retrievable in application search
  # Application status transitions: InProgress → Submitted → UnderReview → Decision
  # Session should be terminated after some time on confirmation page
  # No "Edit" or "Back" links should be present; application is final
  # Printed/PDF version should contain reference number and summary