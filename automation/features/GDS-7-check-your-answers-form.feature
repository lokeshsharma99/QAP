# language: en
@GDS-7 @check-your-answers @universal-credit @wizard-step-4
Feature: Check Your Answers - Universal Credit Application
  As a Universal Credit applicant
  I want to review all my application details before submitting
  So that I can confirm everything is correct and make changes if needed

  Background: Common setup for Check Your Answers page
    Given I am on the "Check Your Answers" step of the Universal Credit application wizard
    And the page has loaded with the GOV.UK design system
    And I have completed all previous wizard steps (Personal Details, Contact Details, Additional Information)

  # =============================================================================
  # POSITIVE PATH SCENARIOS
  # =============================================================================

  @smoke @positive-path
  Scenario: All entered data is displayed correctly in summary sections
    Then I should see a "Personal details" section with summary items
    And the "Personal details" section should display my first name
    And the "Personal details" section should display my last name
    And the "Personal details" section should display my date of birth
    And the "Personal details" section should display my National Insurance number

    And I should see a "Contact details" section with summary items
    And the "Contact details" section should display my email address
    And the "Contact details" section should display my mobile phone number
    And the "Contact details" section should display my address

    And I should see an "Additional information" section with summary items
    And the "Additional information" section should display my marital status
    And the "Additional information" section should display my employment status
    And the "Additional information" section should display my annual gross income

  @regression @positive-path
  Scenario: User can edit information from summary
    When I click the "Edit" link for the "Personal details" section
    Then I should be taken to the "Personal Details" step
    When I update my first name to "Jonathan"
    And I click the "Continue" button
    And I return to the "Check Your Answers" step
    Then the "Personal details" section should display "Jonathan" as my first name

  @regression @positive-path
  Scenario: User can edit contact details from summary
    When I click the "Edit" link for the "Contact details" section
    Then I should be taken to the "Contact Details" step
    And I should see my previously entered data pre-populated

  @regression @positive-path
  Scenario: User can edit additional information from summary
    When I click the "Edit" link for the "Additional information" section
    Then I should be taken to the "Additional Information" step
    And I should see my previously entered data pre-populated

  @smoke @positive-path
  Scenario: Successful application submission with confirmed data
    When I accept the declaration by checking the confirmation checkbox
    And I click the "Accept and send" button
    Then I should proceed to the "Confirmation" step
    And I should see a confirmation reference number

  @regression @positive-path
  Scenario: User can make changes and return to review
    When I click the "Edit" link for the "Personal details" section
    And I update my address in "Contact Details"
    And I click the "Back to check your answers" link
    Then I should return to the "Check Your Answers" step
    And the updated contact address should be displayed

  # =============================================================================
  # ACCEPTANCE CRITERION: All data from previous steps is displayed correctly
  # =============================================================================

  @acceptance-criteria @GDS-7-AC-1
  Scenario: Verify summary displays all submitted data from Personal Details step
    Then the "First name" summary item should display "John"
    And the "Last name" summary item should display "Smith"
    And the "Date of birth" summary item should display "15 June 1990"
    And the "National Insurance number" summary item should display "QQ123456C"

  @acceptance-criteria @GDS-7-AC-2
  Scenario: Verify summary displays all submitted data from Contact Details step
    Then the "Email address" summary item should display "john.smith@example.com"
    And the "Phone number" summary item should display "07700 900123"
    And the "Address" summary item should display "10 Downing Street, Westminster, SW1A 2AA, United Kingdom"

  @acceptance-criteria @GDS-7-AC-3
  Scenario: Verify summary displays all submitted data from Additional Information step
    Then the "Marital status" summary item should display "Single"
    And the "Employment status" summary item should display "Employed full-time"
    And the "Annual income" summary item should display "£25,000"
    And the "Other benefits" summary item should display "No"

  # =============================================================================
  # ACCEPTANCE CRITERION: Edit links navigate to correct step with data preserved
  # =============================================================================

  @acceptance-criteria @GDS-7-AC-4
  Scenario: Edit link for Personal Details navigates correctly and preserves data
    Given I click the "Edit" link for "Personal details"
    When I change my first name from "John" to "Jonathan"
    And I click the "Continue" button to return to Check Your Answers
    Then I should see "Jonathan" in the first name summary

  @acceptance-criteria @GDS-7-AC-5
  Scenario: Edit link for Contact Details navigates correctly and preserves data
    Given I click the "Edit" link for "Contact details"
    When I change my email to "jonathan.smith@example.com"
    And I click the "Continue" button to return to Check Your Answers
    Then I should see "jonathan.smith@example.com" in the email summary

  @acceptance-criteria @GDS-7-AC-6
  Scenario: Edit link for Additional Information navigates correctly and preserves data
    Given I click the "Edit" link for "Additional information"
    When I change my marital status to "Married"
    And I click the "Continue" button to return to Check Your Answers
    Then I should see "Married" in the marital status summary

  # =============================================================================
  # ACCEPTANCE CRITERION: Declaration checkbox required for submission
  # =============================================================================

  @acceptance-criteria @GDS-7-AC-7 @declaration
  Scenario: Submission is blocked if declaration checkbox is not accepted
    When I click the "Accept and send" button without checking the declaration checkbox
    Then the error summary should be displayed
    And the error summary should contain "You must accept the declaration to continue"
    And I should remain on the "Check Your Answers" step

  @regression @declaration
  Scenario: Declaration error is cleared when checkbox is accepted
    When I click the "Accept and send" button without checking the declaration checkbox
    And I check the declaration checkbox
    And I click the "Accept and send" button again
    Then I should proceed to the "Confirmation" step

  # =============================================================================
  # ACCEPTANCE CRITERION: GOV.UK-style error messages displayed
  # =============================================================================

  @acceptance-criteria @GDS-7-AC-8 @error-messages
  Scenario: Verify GOV.UK-style error summary for declaration validation
    When I click the "Accept and send" button without accepting the declaration
    Then the GOV.UK error summary should be displayed
    And the error message should describe the declaration requirement

  @regression @error-messages
  Scenario: Inline error message appears next to declaration checkbox
    When I attempt to submit without accepting the declaration
    Then an error message should appear below the declaration checkbox
    And the declaration checkbox should have an aria-invalid attribute

  # =============================================================================
  # REVIEW PAGE STRUCTURE AND ACCESSIBILITY
  # =============================================================================

  @regression @accessibility
  Scenario: Summary list uses appropriate semantic HTML for screen readers
    Then the page should have a single main heading "Check your answers before sending your application"
    And each summary section should have a heading (h2)
    And summary items should use definition list structure (dl, dt, dd)
    And all summary items should be associated with their edit links

  @regression @accessibility
  Scenario: Edit links are accessible via keyboard navigation
    When I press the Tab key to navigate through the page
    Then each "Edit" link should be focusable in a logical order
    And each "Edit" link should be clearly identifiable as a link

  @regression @accessibility
  Scenario: Error summary links work correctly if form errors exist
    Given I attempt to submit without accepting the declaration
    When I click the "Change" link for the declaration error in the error summary
    Then the declaration checkbox should receive keyboard focus

  # =============================================================================
  # DATA CONSISTENCY CHECKS
  # =============================================================================

  @regression @data-consistency
  Scenario: Data displayed matches what was originally entered
    Given I entered "Jonathan" as my first name in Personal Details
    And I entered "smith.jonathan@example.com" as my email in Contact Details
    And I selected "Married" as my marital status in Additional Information
    When I view the "Check Your Answers" page
    Then the first name should display "Jonathan"
    And the email address should display "smith.jonathan@example.com"
    And the marital status should display "Married"

  @regression @data-consistency
  Scenario: Special characters and formatting are preserved in summary
    Given I entered an email with a plus sign "user+tag@example.com"
    And I entered a hyphenated last name "Smith-Jones"
    And I entered an income with no commas "25000"
    When I view the "Check Your Answers" page
    Then the email should display "user+tag@example.com"
    And the last name should display "Smith-Jones"
    And the income should display formatted as "£25,000"

  # =============================================================================
  # WIZARD NAVIGATION - BACK BUTTONS
  # =============================================================================

  @regression @navigation
  Scenario: Back button returns to previous wizard step
    When I click the "Back" button
    Then I should be taken to the "Additional Information" step
    And my previously entered data should be preserved

  @regression @navigation
  Scenario: Back navigation preserves data across all steps
    When I click the "Back" button twice
    Then I should be taken to the "Contact Details" step
    And my contact details data should be preserved

    When I click the "Back" button again
    Then I should be taken to the "Personal Details" step
    And my personal details data should be preserved

  # =============================================================================
  # DATA REQUIREMENTS DOCUMENTATION
  # =============================================================================

  # Test Data Patterns:
  # All summary data must exactly match previously entered values
  # Declaration checkbox must be unchecked initially, checked to submit
  # Edit links exist for each section: Personal details, Contact details, Additional information
  # Back button navigation should preserve all data across steps
  # Income formatting: displayed with £ symbol and comma thousands separator (e.g., £25,000)
  # Number of summary sections: 3 (Personal, Contact, Additional Information)
  # Declaration text should include: "I confirm that the information I've given is correct and complete"