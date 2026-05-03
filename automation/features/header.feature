Feature: GOV.UK Header Component
  As a citizen
  I want to see the official GOV.UK header with Crown logo, service name, BETA banner, and skip link
  So that I trust the service and can navigate easily.

  Background:
    Given the user is on the home page

  @AC-001
  Scenario: Crown logo and GOV.UK name are present in the header
    Then the header should contain the Crown logo and the GOV.UK name

  @AC-002
  Scenario: Service name "Apply for Universal Credit" is visible in the header
    Then the header should contain the service name "Apply for Universal Credit"

  @AC-003
  Scenario: BETA banner is displayed below the header
    Then the BETA banner should be visible below the header

  @AC-004
  Scenario: Header layout is responsive on mobile, tablet, and desktop
    Then the header should be readable and functional on mobile, tablet, and desktop viewports

  @AC-005
  Scenario: Skip to main content link is present at the top of the page
    Then the skip to main content link should be present at the top of the page