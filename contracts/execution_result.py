"""
Execution Result Contract
==========================

Pydantic models for test execution results.
The ExecutionResult represents the outcome of running Playwright tests,
including pass/fail status, execution time, and detailed failure information.
"""

from enum import Enum

from pydantic import BaseModel, Field


class TestStatus(str, Enum):
    """Status of a test execution."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestResult(BaseModel):
    """Result of a single test scenario."""

    scenario_name: str = Field(description="Name of the test scenario")
    status: TestStatus = Field(description="Pass/fail status of the test")
    duration_ms: int = Field(description="Execution time in milliseconds")
    error_message: str = Field(default="", description="Error message if failed")
    screenshot_path: str = Field(default="", description="Path to failure screenshot")
    trace_path: str = Field(default="", description="Path to trace.zip if failed")
    steps_passed: int = Field(default=0, description="Number of steps passed")
    steps_failed: int = Field(default=0, description="Number of steps failed")


class ExecutionResult(BaseModel):
    """Complete execution result for a test run.

    Produced after running Playwright tests.
    Used by Operations Team for failure analysis and healing.
    """

    run_id: str = Field(description="Unique identifier for this test run")
    timestamp: str = Field(description="ISO 8601 timestamp of the execution")
    total_scenarios: int = Field(description="Total number of test scenarios executed")
    passed: int = Field(description="Number of scenarios passed")
    failed: int = Field(description="Number of scenarios failed")
    skipped: int = Field(description="Number of scenarios skipped")
    duration_ms: int = Field(description="Total execution time in milliseconds")
    test_results: list[TestResult] = Field(
        default_factory=list,
        description="Detailed results for each scenario"
    )
    browser: str = Field(default="chromium", description="Browser used for execution")
    environment: str = Field(default="test", description="Target environment")
    base_url: str = Field(description="Base URL of the application under test")
    report_path: str = Field(default="", description="Path to the HTML report")
    has_failures: bool = Field(default=False, description="Whether any tests failed")
    failure_summary: str = Field(default="", description="Summary of failures if any")
