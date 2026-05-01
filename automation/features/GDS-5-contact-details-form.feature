# language: en
@GDS-5 @contact-details @universal-credit @wizard-step-2
Feature: Contact Details Form - Universal Credit Application
  As a Universal Credit applicant
  I want to enter my contact details
  So that the Department for Work and Pensions can contact me about my application

  Background: Common setup for Contact Details form
    Given I am on the "Contact Details" step of the Universal Credit application wizard
    And the page has loaded with the GOV.UK design system

  # =============================================================================
  # POSITIVE PATH SCENARIOS
  # =============================================================================

  @smoke @positive-path
  Scenario: Successfully submit Contact Details with all valid fields
    When I enter "john.smith@example.com" in the "Email address" field
    And I enter "07700 900123" in the "Mobile phone number" field
    And I select "United Kingdom" from the "Country" field
    And I enter "10 Downing Street" in the "Address line 1" field
    And I enter "Westminster" in the "Town or city" field
    And I enter "SW1A 2AA" in the "Postcode" field
    And I click the "Continue" button
    Then I should proceed to the "Additional Information" step of the wizard

  @regression @positive-path
  Scenario: User can edit previously entered contact details
    Given I have previously entered valid contact details
    When I view the "Contact Details" step
    Then all previously entered fields should be populated and editable

  # =============================================================================
  # ACCEPTANCE CRITERION: All fields visible and editable
  # =============================================================================

  @acceptance-criteria @GDS-5-AC-1
  Scenario: Verify all Contact Details form fields are visible and interactive
    Then the "Email address" field should be visible and editable
    And the "Mobile phone number" field should be visible and editable
    And the "Country" field should be visible and editable
    And the "Address line 1" field should be visible and editable
    And the "Town or city" field should be visible and editable
    And the "Postcode" field should be visible and editable
    And the "Continue" button should be visible

  # =============================================================================
  # ACCEPTANCE CRITERION: Required field validation on blur/submit
  # =============================================================================

  @regression @required-field-validation
  Scenario: Display validation error when Email is missing
    When I leave the "Email address" field empty
    And I blur the field
    Then the "Email address" field should show error "Enter your email address"
    And the error summary should contain "Enter your email address"

  @regression @required-field-validation
  Scenario: Display validation error when Mobile phone number is missing
    When I leave the "Mobile phone number" field empty
    And I blur the field
    Then the "Mobile phone number" field should show error "Enter your mobile phone number"
    And the error summary should contain "Enter your mobile phone number"

  @regression @required-field-validation
  Scenario: Display validation error when Address line 1 is missing
    When I leave the "Address line 1" field empty
    And I blur the field
    Then the "Address line 1" field should show error "Enter your address"
    And the error summary should contain "Enter your address"

  @regression @required-field-validation
  Scenario: Display validation error when Town or city is missing
    When I leave the "Town or city" field empty
    And I blur the field
    Then the "Town or city" field should show error "Enter your town or city"
    And the error summary should contain "Enter your town or city"

  @regression @required-field-validation
  Scenario: Display validation error when Postcode is missing
    When I leave the "Postcode" field empty
    And I blur the field
    Then the "Postcode" field should show error "Enter your postcode"
    And the error summary should contain "Enter your postcode"

  @acceptance-criteria @GDS-5-AC-2 @required-field-validation
  Scenario: Submit form with all required fields empty triggers validation
    When I click the "Continue" button without entering any data
    Then the error summary should be displayed
    And the error summary should contain "Enter your email address"
    And the error summary should contain "Enter your mobile phone number"
    And the error summary should contain "Enter your address"
    And the error summary should contain "Enter your town or city"
    And the error summary should contain "Enter your postcode"

  # =============================================================================
  # ACCEPTANCE CRITERION: Email format validation
  # =============================================================================

  @acceptance-criteria @GDS-5-AC-3 @format-validation
  Scenario: Reject email with invalid format - missing @ symbol
    When I enter "johnexample.com" in the "Email address" field
    And I blur the field
    Then the "Email address" field should show error "Enter your email address in the correct format, like name@example.com"

  @regression @format-validation
  Scenario: Reject email with invalid format - no domain
    When I enter "john@" in the "Email address" field
    And I blur the field
    Then the "Email address" field should show error "Enter your email address in the correct format, like name@example.com"

  @regression @format-validation
  Scenario: Accept email with valid format variations
    When I enter "user+tag@example.co.uk" in the "Email address" field
    Then the field should accept the valid email format

    When I enter "firstname.lastname@example.com" in the "Email address" field
    Then the field should accept the valid email format

  # =============================================================================
  # ACCEPTANCE CRITERION: Phone number format validation
  # =============================================================================

  @acceptance-criteria @GDS-5-AC-4 @format-validation
  Scenario: Reject phone number with invalid format - too short
    When I enter "07700" in the "Mobile phone number" field
    And I blur the field
    Then the "Mobile phone number" field should show error "Enter your mobile phone number, like 07700 900123 or +44 7700 900123"

  @regression @format-validation
  Scenario: Reject phone number with invalid format - contains letters
    When I enter "07700 ABCDEF" in the "Mobile phone number" field
    And I blur the field
    Then the "Mobile phone number" field should show error "Enter your mobile phone number, like 07700 900123 or +44 7700 900123"

  @regression @format-validation
  Scenario: Accept phone number with valid UK format
    When I enter "07700 900987" in the "Mobile phone number" field
    Then the field should accept the valid phone format

    When I enter "+44 7700 900987" in the "Mobile phone number" field
    Then the field should accept the valid phone format

  # =============================================================================
  # ACCEPTANCE CRITERION: Postcode format validation
  # =============================================================================

  @acceptance-criteria @GDS-5-AC-5 @format-validation
  Scenario: Reject postcode with invalid format
    When I enter "ABC123" in the "Postcode" field
    And I blur the field
    Then the "Postcode" field should show error "Enter your postcode, like AA1 2BB"

  @regression @format-validation
  Scenario: Accept postcode with valid UK format variations
    When I enter "SW1A 2AA" in the "Postcode" field
    Then the field should accept the valid postcode format

    When I enter "M1 1AA" in the "Postcode" field
    Then the field should accept the valid postcode format

    When I enter "CR2 6XH" in the "Postcode" field
    Then the field should accept the valid postcode format

  # =============================================================================
  # ACCEPTANCE CRITERION: User cannot proceed without valid inputs
  # =============================================================================

  @acceptance-criteria @GDS-5-AC-6 @navigation-blocking
  Scenario: User cannot proceed with missing required fields
    Given I have entered valid data in all but one field
    When I click the "Continue" button
    Then I should remain on the "Contact Details" step
    And the missing required field should show appropriate error

  @regression @navigation-blocking
  Scenario: User cannot proceed with any invalid field
    When I enter "john.smith@example.com" in the "Email address" field
    And I enter "07700 900123" in the "Mobile phone number" field
    And I enter "10 Downing Street" in the "Address line 1" field
    And I enter "Westminster" in the "Town or city" field
    And I enter "INVALID" in the "Postcode" field
    And I click the "Continue" button
    Then I should remain on the "Contact Details" step
    And the "Postcode" field should show error "Enter your postcode, like AA1 2BB"

  # =============================================================================
  # ACCEPTANCE CRITERION: GOV.UK-style error messages displayed
  # =============================================================================

  @acceptance-criteria @GDS-5-AC-7 @error-messages
  Scenario: Verify GOV.UK-style error summary is displayed for form validation errors
    When I click the "Continue" button without entering any data
    Then the GOV.UK error summary should be displayed
    And the error summary should contain multiple validation errors

  @regression @error-messages
  Scenario: Verify inline error messages are displayed next to invalid fields
    When I leave the "Email address" field empty
    And I blur the field
    Then an inline error message should appear below the "Email address" field
    And the error should be announced to assistive technology

  # =============================================================================
  # INTERNATIONAL ADDRESS OPTIONS
  # =============================================================================

  @regression @international-address
  Scenario: Non-UK address fields appear when Country is not United Kingdom
    When I select "France" from the "Country" field
    Then the "Address line 1" field should be visible
    And the "Town or city" field should be visible
    And the "Postcode" field should not be visible or marked as not applicable
    And a "State or province" field should be visible for international addresses

  @regression @international-address
  Scenario: UK address validation only applies when United Kingdom is selected
    Given I select "United Kingdom" from the "Country" field
    When I enter "SW1A 2AA" in the "Postcode" field
    Then the field should accept the valid UK postcode format

  # =============================================================================
  # DATA REQUIREMENTS DOCUMENTATION
  # =============================================================================

  # Test Data Patterns:
  # Valid emails: john.smith@example.com, user+tag@example.co.uk, firstname.lastname@example.com
  # Invalid emails: johnexample.com, john@, name@.com
  # Valid UK phones: 07700 900123, +44 7700 900987
  # Invalid phones: 07700 (too short), 07700 ABCDEF (contains letters)
  # Valid UK postcodes: SW1A 2AA, M1 1AA, CR2 6XH
  # Invalid postcodes: ABC123, 12345 (wrong format)