"""
RCA Report Contract
===================

Root Cause Analysis report for test failures.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class FailureClassification(str, Enum):
    """Classification of failure types."""
    LOCATOR_STALE = "LOCATOR_STALE"
    DATA_MISMATCH = "DATA_MISMATCH"
    TIMING_FLAKE = "TIMING_FLAKE"
    ENV_FAILURE = "ENV_FAILURE"
    LOGIC_CHANGE = "LOGIC_CHANGE"
    UNKNOWN = "UNKNOWN"


class LocatorInfo(BaseModel):
    """Information about a locator that failed."""
    selector: str = Field(description="The locator string that failed")
    page: str = Field(description="The page object containing the locator")
    line_number: Optional[int] = Field(default=None, description="Line number in the file")
    element_type: Optional[str] = Field(default=None, description="Type of element (button, input, etc.)")


class RCAReport(BaseModel):
    """Root Cause Analysis report for a test failure."""
    
    # Failure identification
    test_name: str = Field(description="Name of the failing test")
    failure_type: FailureClassification = Field(description="Classification of the failure")
    confidence: float = Field(description="Confidence score (0-100)", ge=0, le=100)
    
    # Root cause details
    root_cause: str = Field(description="Detailed explanation of the root cause")
    affected_locator: Optional[LocatorInfo] = Field(default=None, description="Locator that caused the failure")
    
    # Context
    trace_file: Optional[str] = Field(default=None, description="Path to the trace.zip file")
    error_message: str = Field(description="Error message from the test failure")
    stack_trace: Optional[str] = Field(default=None, description="Stack trace if available")
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list, description="Recommended actions to fix the issue")
    is_healable: bool = Field(default=False, description="Whether the issue can be auto-healed")
    
    # Metadata
    timestamp: str = Field(description="Timestamp when the analysis was performed")
    agent_id: str = Field(description="ID of the agent that performed the analysis")
    
    class Config:
        json_schema_extra = {
            "example": {
                "test_name": "UC-001: Personal Details Form Submission",
                "failure_type": "LOCATOR_STALE",
                "confidence": 95.0,
                "root_cause": "Element with selector 'button[name=\"continue\"]' no longer exists on the page. The button structure changed from button to div.",
                "affected_locator": {
                    "selector": "button[name=\"continue\"]",
                    "page": "UniversalCreditPersonalDetailsPage",
                    "line_number": 29,
                    "element_type": "button"
                },
                "trace_file": "/traces/uc-001-failure.zip",
                "error_message": "locator.click: Target closed",
                "stack_trace": "Error: Target closed\n    at UniversalCreditPersonalDetailsPage.clickContinue",
                "recommendations": [
                    "Update selector to use role-based locator: getByRole('button', {name: /continue/i})",
                    "Verify the new selector with Playwright MCP before applying"
                ],
                "is_healable": True,
                "timestamp": "2025-04-13T01:30:00Z",
                "agent_id": "detective"
            }
        }
