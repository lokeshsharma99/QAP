# language: en
@GDS-6 @additional-information @universal-credit @wizard-step-3
Feature: Additional Information Form - Universal Credit Application
  As a Universal Credit applicant
  I want to provide additional information about my circumstances
  So that the Department for Work and Pensions has all the information needed to process my claim

  Background: Common setup for Additional Information form
    Given I am on the "Additional Information" step of the Universal Credit application wizard
    And the page has loaded with the GOV.UK design system
    And I have previously entered valid personal and contact details

  # =============================================================================
  # POSITIVE PATH SCENARIOS
  # =============================================================================

  @smoke @positive-path
  Scenario: Successfully submit Additional Information with all valid fields
    When I select "Single" from the "Marital status" field
    And I select "No" from the "Do you have any children?" field
    And I enter "Employed full-time" in the "Current employment status" field
    And I enter "50000" in the "Annual gross income" field
    And I select "No" from the "Do you receive any other benefits?" field
    And I click the "Continue" button
    Then I should proceed to the "Check Your Answers" step of the wizard

  @regression @positive-path
  Scenario: User with children provides child details
    When I select "Yes" from the "Do you have any children?" field
    Then a child details section should be displayed
    When I enter "2" in the "Number of children" field
    And I enter "10" and "12" in the "Children's ages" fields
    And I click the "Continue" button
    Then I should proceed to the "Check Your Answers" step of the wizard

  @regression @positive-path
  Scenario: User with other benefits provides benefit details
    When I select "Yes" from the "Do you receive any other benefits?" field
    Then a benefits details section should be displayed
    When I enter " Disability Living Allowance" in the "Benefit type" field
    And I enter "2020" in the "Year started receiving" field
    And I click the "Continue" button
    Then I should proceed to the "Check Your Answers" step of the wizard

  # =============================================================================
  # ACCEPTANCE CRITERION: All fields visible and editable
  # =============================================================================

  @acceptance-criteria @GDS-6-AC-1
  Scenario: Verify all Additional Information form fields are visible and interactive
    Then the "Marital status" field should be visible and editable
    And the "Do you have any children?" field should be visible and editable
    And the "Current employment status" field should be visible and editable
    And the "Annual gross income" field should be visible and editable
    And the "Do you receive any other benefits?" field should be visible and editable
    And the "Continue" button should be visible

  # =============================================================================
  # ACCEPTANCE CRITERION: Conditional fields revealed based on user selections
  # =============================================================================

  @acceptance-criteria @GDS-6-AC-2
  Scenario: Child details section appears when user selects they have children
    When I select "Yes" from the "Do you have any children?" field
    Then the child details section should be displayed
    And the "Number of children" field should be visible and editable
    And the "Children's ages" field should be visible and editable

  @acceptance-criteria @GDS-6-AC-3
  Scenario: Benefits details section appears when user selects they receive other benefits
    When I select "Yes" from the "Do you receive any other benefits?" field
    Then the benefits details section should be displayed
    And the "Benefit type" field should be visible and editable
    And the "Year started receiving" field should be visible and editable

  @acceptance-criteria @GDS-6-AC-4
  Scenario: Conditional sections are hidden when selecting 'No'
    Given I have previously opened the child details section
    When I select "No" from the "Do you have any children?" field
    Then the child details section should be hidden

  # =============================================================================
  # ACCEPTANCE CRITERION: Required field validation on blur/submit
  # =============================================================================

  @regression @required-field-validation
  Scenario: Display validation error when Marital status is missing
    When I leave the "Marital status" field empty
    And I blur the field
    Then the "Marital status" field should show error "Select your marital status"
    And the error summary should contain "Select your marital status"

  @regression @required-field-validation
  Scenario: Display validation error when Employment status is missing
    When I leave the "Current employment status" field empty
    And I blur the field
    Then the "Current employment status" field should show error "Enter your employment status"
    And the error summary should contain "Enter your employment status"

  @acceptance-criteria @GDS-6-AC-5 @required-field-validation
  Scenario: Submit form with all required fields empty triggers validation
    When I click the "Continue" button without entering any data
    Then the error summary should be displayed
    And the error summary should contain "Select your marital status"
    And the error summary should contain "Enter your employment status"
    And the error summary should contain "Enter your annual gross income"

  # =============================================================================
  # ACCEPTANCE CRITERION: Numerical field validation
  # =============================================================================

  @acceptance-criteria @GDS-6-AC-6 @format-validation
  Scenario: Reject negative income value
    When I enter "-50000" in the "Annual gross income" field
    And I blur the field
    Then the "Annual gross income" field should show error "Enter a valid income amount"

  @regression @format-validation
  Scenario: Reject income with decimal places (should be whole pounds)
    When I enter "50000.50" in the "Annual gross income" field
    And I blur the field
    Then the "Annual gross income" field should show error "Enter your income as a whole number, without pence"

  @regression @format-validation
  Scenario: Accept valid income value
    When I enter "25000" in the "Annual gross income" field
    Then the field should accept the valid income format

  # =============================================================================
  # ACCEPTANCE CRITERION: Year validation for benefit start date
  # =============================================================================

  @acceptance-criteria @GDS-6-AC-7 @format-validation
  Scenario: Reject future year for benefit start date
    When I select "Yes" from the "Do you receive any other benefits?" field
    And I enter "2030" in the "Year started receiving" field
    And I blur the field
    Then the "Year started receiving" field should show error "Enter a valid year in the past"

  @regression @format-validation
  Scenario: Accept reasonable past year for benefit start date
    When I enter "2015" in the "Year started receiving" field
    Then the field should accept the valid year format

  # =============================================================================
  # ACCEPTANCE CRITERION: User cannot proceed without valid inputs
  # =============================================================================

  @acceptance-criteria @GDS-6-AC-8 @navigation-blocking
  Scenario: User cannot proceed with missing required fields
    Given I have entered valid data in all but one required field
    When I click the "Continue" button
    Then I should remain on the "Additional Information" step
    And the missing required field should show appropriate error

  @regression @navigation-blocking
  Scenario: User cannot proceed with invalid conditional field
    When I select "Yes" from the "Do you have any children?" field
    And I enter "two" in the "Number of children" field
    And I click the "Continue" button
    Then I should remain on the "Additional Information" step
    And the "Number of children" field should show error "Enter a whole number"

  # =============================================================================
  # ACCEPTANCE CRITERION: GOV.UK-style error messages displayed
  # =============================================================================

  @acceptance-criteria @GDS-6-AC-9 @error-messages
  Scenario: Verify GOV.UK-style error summary is displayed for form validation errors
    When I click the "Continue" button without entering any data
    Then the GOV.UK error summary should be displayed
    And the error summary should contain multiple validation errors

  @regression @error-messages
  Scenario: Verify inline error messages are displayed next to invalid fields
    When I leave the "Marital status" field empty
    And I blur the field
    Then an inline error message should appear below the "Marital status" field
    And the error should be announced to assistive technology

  # =============================================================================
  # DATA PERSISTENCE ACROSS WIZARD
  # =============================================================================

  @regression @data-persistence
  Scenario: Data entered in previous steps is not lost
    Given I have completed the Personal Details step with valid data
    And I have completed the Contact Details step with valid data
    When I view the "Additional Information" step
    Then my previously entered data should still be intact

  # =============================================================================
  # DATA REQUIREMENTS DOCUMENTATION
  # =============================================================================

  # Test Data Patterns:
  # Valid marital statuses: Single, Married, Civil partnered, Divorced, Widowed
  # Valid employment statuses: Employed full-time, Employed part-time, Self-employed, Unemployed, Student, Retired
  # Income: Whole pounds only, positive values, realistic range (0 - 200000)
  # Children: Whole numbers (0-20 range reasonable)
  # Years: 1900 - current year for benefit start dates
  # Conditional fields: Only required if parent section answers "Yes"