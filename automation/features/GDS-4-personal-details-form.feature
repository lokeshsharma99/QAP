# language: en
@GDS-4 @personal-details @universal-credit @wizard-step-1
Feature: Personal Details Form - Universal Credit Application
  As a Universal Credit applicant
  I want to enter my personal details
  So that I can begin my application process

  Background: Common setup for Personal Details form
    Given I am on the "Personal Details" step of the Universal Credit application wizard
    And the page has loaded with the GOV.UK design system

  # =============================================================================
  # POSITIVE PATH SCENARIOS
  # =============================================================================

  @smoke @positive-path
  Scenario: Successfully submit Personal Details form with all valid fields
    When I enter "John" in the "First name" field
    And I enter "Smith" in the "Last name" field
    And I enter "15" in the "Day" field for date of birth
    And I enter "06" in the "Month" field for date of birth
    And I enter "1990" in the "Year" field for date of birth
    And I enter "QQ123456C" in the "National Insurance number" field
    And I click the "Continue" button
    Then I should proceed to the "Contact Details" step of the wizard

  @regression @positive-path
  Scenario: User can edit previously entered data in Personal Details form
    Given I have previously entered valid personal details
    When I view the "Personal Details" step
    Then all previously entered fields should be populated and editable

  @regression @positive-path
  Scenario: Maximum valid NI Number format is accepted
    When I enter "QQ123456C" in the "National Insurance number" field
    Then the field should accept the valid NI Number format

  # =============================================================================
  # ACCEPTANCE CRITERION: All fields visible and editable
  # =============================================================================

  @acceptance-criteria @GDS-4-AC-1
  Scenario: Verify all Personal Details form fields are visible and interactive
    Then the "First name" field should be visible and editable
    And the "Last name" field should be visible and editable
    And the "Day" field for date of birth should be visible and editable
    And the "Month" field for date of birth should be visible and editable
    And the "Year" field for date of birth should be visible and editable
    And the "National Insurance number" field should be visible and editable
    And the "Continue" button should be visible

  # =============================================================================
  # ACCEPTANCE CRITERION: Required field validation on blur/submit
  # =============================================================================

  @regression @required-field-validation
  Scenario: Display validation error when First Name is missing
    When I leave the "First name" field empty
    And I blur the field
    Then the "First name" field should show error "Enter your first name"
    And the error summary should contain "Enter your first name"

  @regression @required-field-validation
  Scenario: Display validation error when Last Name is missing
    When I leave the "Last name" field empty
    And I blur the field
    Then the "Last name" field should show error "Enter your last name"
    And the error summary should contain "Enter your last name"

  @regression @required-field-validation
  Scenario: Display validation error when Date of Birth is missing
    When I leave the date of birth fields empty
    And I blur the fields
    Then the date of birth field should show error "Enter your date of birth"
    And the error summary should contain "Enter your date of birth"

  @regression @required-field-validation
  Scenario: Display validation error when National Insurance Number is missing
    When I leave the "National Insurance number" field empty
    And I blur the field
    Then the "National Insurance number" field should show error "Enter a valid National Insurance number"
    And the error summary should contain "Enter a valid National Insurance number"

  @acceptance-criteria @GDS-4-AC-2 @required-field-validation
  Scenario: Submit form with all required fields empty triggers validation
    When I click the "Continue" button without entering any data
    Then the error summary should be displayed
    And the error summary should contain "Enter your first name"
    And the error summary should contain "Enter your last name"
    And the error summary should contain "Enter your date of birth"
    And the error summary should contain "Enter a valid National Insurance number"

  # =============================================================================
  # ACCEPTANCE CRITERION: NI Number format validation
  # =============================================================================

  @acceptance-criteria @GDS-4-AC-3 @format-validation
  Scenario: Reject NI Number with incorrect format - too short
    When I enter "QQ1234" in the "National Insurance number" field
    And I blur the field
    Then the "National Insurance number" field should show error "Enter a valid National Insurance number"

  @regression @format-validation
  Scenario: Reject NI Number with incorrect format - all digits
    When I enter "123456789" in the "National Insurance number" field
    And I blur the field
    Then the "National Insurance number" field should show error "Enter a valid National Insurance number"

  @regression @format-validation
  Scenario: Reject NI Number with incorrect format - all letters
    When I enter "QQQQQQQQQ" in the "National Insurance number" field
    And I blur the field
    Then the "National Insurance number" field should show error "Enter a valid National Insurance number"

  @regression @format-validation
  Scenario: Reject NI Number with incorrect format - invalid prefix letters
    When I enter "DQ123456C" in the "National Insurance number" field
    And I blur the field
    Then the "National Insurance number" field should show error "Enter a valid National Insurance number"

  @regression @format-validation
  Scenario: Accept NI Number with valid format variations
    When I enter "AB123456C" in the "National Insurance number" field
    Then the field should accept the valid NI Number format

    When I enter "WX123456Z" in the "National Insurance number" field
    Then the field should accept the valid NI Number format

  # =============================================================================
  # ACCEPTANCE CRITERION: User cannot proceed without valid inputs
  # =============================================================================

  @acceptance-criteria @GDS-4-AC-4 @navigation-blocking
  Scenario: User cannot proceed with missing required fields
    Given I have entered valid data in all but one field
    When I click the "Continue" button
    Then I should remain on the "Personal Details" step
    And the missing required field should show appropriate error

  @regression @navigation-blocking
  Scenario: User cannot proceed with any invalid field
    When I enter "John" in the "First name" field
    And I enter "Smith" in the "Last name" field
    And I enter "15" in the "Day" field for date of birth
    And I enter "06" in the "Month" field for date of birth
    And I enter "1990" in the "Year" field for date of birth
    And I enter "INVALID" in the "National Insurance number" field
    And I click the "Continue" button
    Then I should remain on the "Personal Details" step
    And the "National Insurance number" field should show error "Enter a valid National Insurance number"

  # =============================================================================
  # ACCEPTANCE CRITERION: GOV.UK-style error messages displayed
  # =============================================================================

  @acceptance-criteria @GDS-4-AC-5 @error-messages
  Scenario: Verify GOV.UK-style error summary is displayed for form validation errors
    When I click the "Continue" button without entering any data
    Then the GOV.UK error summary should be displayed
    And the error summary should contain multiple validation errors

  @regression @error-messages
  Scenario: Verify inline error messages are displayed next to invalid fields
    When I leave the "First name" field empty
    And I blur the field
    Then an inline error message should appear below the "First name" field
    And the error should be announced to assistive technology

  @regression @error-messages
  Scenario: Clicking error summary link focuses on the invalid field
    When I leave the "First name" field empty
    And I submit the form with errors
    And I click on the error link for "Enter your first name" in the error summary
    Then the "First name" field should be focused

  # =============================================================================
  # DATE OF BIRTH VALIDATION SCENARIOS
  # =============================================================================

  @regression @date-validation
  Scenario: Reject future date of birth
    When I enter "John" in the "First name" field
    And I enter "Smith" in the "Last name" field
    And I enter "15" in the "Day" field for date of birth
    And I enter "06" in the "Month" field for date of birth
    And I enter "2099" in the "Year" field for date of birth
    And I enter "QQ123456C" in the "National Insurance number" field
    And I click the "Continue" button
    Then the date of birth field should show error "Enter your date of birth"
    And I should remain on the "Personal Details" step

  @regression @date-validation
  Scenario: Reject user under 18 years of age
    When I enter "John" in the "First name" field
    And I enter "Smith" in the "Last name" field
    And I enter "15" in the "Day" field for date of birth
    And I enter "06" in the "Month" field for date of birth
    And I enter "2010" in the "Year" field for date of birth
    And I enter "QQ123456C" in the "National Insurance number" field
    And I click the "Continue" button
    Then the date of birth field should show error "Enter your date of birth"
    And I should remain on the "Personal Details" step

  @regression @date-validation
  Scenario: Reject invalid date format (non-numeric values)
    When I enter "John" in the "First name" field
    And I enter "AA" in the "Day" field for date of birth
    And I blur the field
    Then the date of birth field should show error "Enter your date of birth"

  # =============================================================================
  # DATA REQUIREMENTS DOCUMENTATION
  # =============================================================================
  
  # Test Data Patterns:
  # Valid NI Numbers: QQ123456C, AB123456C, WX123456Z — format: 2 letters, 6 digits, 1 letter
  # Invalid NI Numbers: QQ1234 (too short), 123456789 (all digits), INVALID (all letters)
  # Valid DOB: Any date that results in user being 18+ years old and in the past
  # Invalid DOB: Future dates, dates making user under 18