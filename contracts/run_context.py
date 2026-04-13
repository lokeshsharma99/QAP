"""
Run Context Contract
=====================

Pydantic models for test data provisioning and execution context.
The RunContext represents the data and configuration needed to execute
a Playwright test, including test users, database seed data, API mocks,
and cleanup queries.
"""

from pydantic import BaseModel, Field


class TestUser(BaseModel):
    """A test user account for automation testing."""

    username: str = Field(description="Username for the test user")
    password: str = Field(description="Password for the test user")
    email: str = Field(default="", description="Email address (may be masked)")
    phone: str = Field(default="", description="Phone number (may be masked)")
    national_insurance_number: str = Field(
        default="",
        description="National Insurance Number (must be masked in logs)"
    )
    address: str = Field(default="", description="Street address (may be masked)")
    postcode: str = Field(default="", description="Postal code")
    date_of_birth: str = Field(default="", description="Date of birth (YYYY-MM-DD)")
    pii_masked: bool = Field(
        default=True,
        description="Whether PII fields have been masked for logging"
    )
    custom_fields: dict[str, str] = Field(
        default_factory=dict,
        description="Any additional custom fields for the test user"
    )
    field_types: dict[str, str] = Field(
        default_factory=dict,
        description="Field type configuration: 'text_input' (dynamic) or 'lookup_dropdown' (static)"
    )


class RunContext(BaseModel):
    """Execution context for a Playwright test run.

    Produced by the Data Agent.
    Used by the Engineer Agent to generate tests with appropriate test data.
    """

    test_user: TestUser = Field(
        description="Test user credentials and PII data"
    )
    db_seed_queries: list[str] = Field(
        default_factory=list,
        description="SQL queries to seed the database before test execution"
    )
    api_mocks: dict[str, dict] = Field(
        default_factory=dict,
        description="API endpoint mocks (endpoint_url -> mock_response)"
    )
    cleanup_queries: list[str] = Field(
        default_factory=list,
        description="SQL queries to clean up test data after execution"
    )
    environment: str = Field(
        default="test",
        description="Target environment (test, staging, production)"
    )
    base_url: str = Field(
        default="",
        description="Base URL of the application under test"
    )
    browser_config: dict[str, str] = Field(
        default_factory=dict,
        description="Browser configuration (viewport, device, etc.)"
    )
    timeout_ms: int = Field(
        default=30000,
        description="Default timeout for page operations in milliseconds"
    )
    retry_on_failure: bool = Field(
        default=False,
        description="Whether to retry failed test steps"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed steps"
    )
