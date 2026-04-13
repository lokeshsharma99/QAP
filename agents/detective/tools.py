"""
Detective Agent Tools
=====================

Tools for analyzing test failures and generating RCA reports.
"""

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from agno.tools import tool
from agno.tools.file import FileTools
from pydantic import BaseModel

from contracts.rca_report import FailureClassification, LocatorInfo, RCAReport


@tool(
    name="analyze_trace_file",
    description="Analyze a Playwright trace.zip file to identify the root cause of test failure",
)
def analyze_trace_file(
    trace_file_path: str,
    test_name: str,
    error_message: str,
    stack_trace: Optional[str] = None,
) -> str:
    """Analyze a Playwright trace file to identify root cause.

    Args:
        trace_file_path: Path to the trace.zip file
        test_name: Name of the failing test
        error_message: Error message from the test failure
        stack_trace: Stack trace if available

    Returns:
        JSON string with RCAReport
    """
    # Initialize report with basic info
    report = RCAReport(
        test_name=test_name,
        error_message=error_message,
        stack_trace=stack_trace,
        trace_file=trace_file_path,
        timestamp=datetime.utcnow().isoformat() + "Z",
        agent_id="detective",
    )
    
    # Analyze error message to classify failure
    failure_type = _classify_failure(error_message, stack_trace)
    report.failure_type = failure_type
    
    # Determine confidence based on classification
    report.confidence = _calculate_confidence(failure_type, error_message)
    
    # Extract locator information if available
    locator_info = _extract_locator_info(error_message, stack_trace)
    if locator_info:
        report.affected_locator = locator_info
    
    # Generate root cause explanation
    report.root_cause = _generate_root_cause(failure_type, error_message, locator_info)
    
    # Generate recommendations
    report.recommendations = _generate_recommendations(failure_type, locator_info)
    
    # Determine if healable
    report.is_healable = (failure_type == FailureClassification.LOCATOR_STALE and 
                         locator_info is not None)
    
    return json.dumps(report.model_dump(), indent=2)


def _classify_failure(error_message: str, stack_trace: Optional[str]) -> FailureClassification:
    """Classify the failure type based on error patterns."""
    error_lower = error_message.lower()
    
    # Locator failures
    if any(keyword in error_lower for keyword in [
        "target closed", "element not found", "locator.click", 
        "selector not found", "timeout exceeded"
    ]):
        return FailureClassification.LOCATOR_STALE
    
    # Data mismatches
    if any(keyword in error_lower for keyword in [
        "assertion error", "expected", "actual", "data mismatch"
    ]):
        return FailureClassification.DATA_MISMATCH
    
    # Timing issues
    if any(keyword in error_lower for keyword in [
        "timeout", "flaky", "race condition"
    ]):
        return FailureClassification.TIMING_FLAKE
    
    # Environment failures
    if any(keyword in error_lower for keyword in [
        "network error", "connection refused", "service unavailable", "503"
    ]):
        return FailureClassification.ENV_FAILURE
    
    # Default to unknown
    return FailureClassification.UNKNOWN


def _calculate_confidence(failure_type: FailureClassification, error_message: str) -> float:
    """Calculate confidence score based on classification and error clarity."""
    base_confidence = {
        FailureClassification.LOCATOR_STALE: 95.0,
        FailureClassification.DATA_MISMATCH: 85.0,
        FailureClassification.TIMING_FLAKE: 70.0,
        FailureClassification.ENV_FAILURE: 80.0,
        FailureClassification.LOGIC_CHANGE: 75.0,
        FailureClassification.UNKNOWN: 50.0,
    }
    
    confidence = base_confidence.get(failure_type, 50.0)
    
    # Adjust based on error message clarity
    if len(error_message) > 100:
        confidence += 5.0
    if "locator" in error_message.lower():
        confidence += 5.0
    
    return min(confidence, 100.0)


def _extract_locator_info(error_message: str, stack_trace: Optional[str]) -> Optional[LocatorInfo]:
    """Extract locator information from error message or stack trace."""
    # Try to extract selector from error message
    if "locator" in error_message.lower() or "selector" in error_message.lower():
        # Simple extraction - in real implementation, would use regex
        selector = _extract_selector(error_message)
        if selector:
            return LocatorInfo(
                selector=selector,
                page="Unknown",  # Would be extracted from stack trace
                element_type="Unknown",  # Would be inferred from selector
            )
    
    return None


def _extract_selector(text: str) -> Optional[str]:
    """Extract selector string from error message."""
    # Simple placeholder implementation
    # In real implementation, would use regex to extract CSS/XPath selectors
    if "[" in text and "]" in text:
        start = text.find("[")
        end = text.rfind("]") + 1
        return text[start:end]
    return None


def _generate_root_cause(failure_type: FailureClassification, error_message: str, 
                          locator_info: Optional[LocatorInfo]) -> str:
    """Generate detailed root cause explanation."""
    explanations = {
        FailureClassification.LOCATOR_STALE: f"The locator '{locator_info.selector if locator_info else 'unknown'}' no longer matches any element on the page. The element structure or attributes may have changed.",
        FailureClassification.DATA_MISMATCH: f"Test data does not match the expected format. The application may have changed validation rules or data requirements.",
        FailureClassification.TIMING_FLAKE: f"Test failed due to timing issues. The element may not have been ready for interaction when the test attempted to interact with it.",
        FailureClassification.ENV_FAILURE: f"Test failed due to environment issues (network, service availability, etc.). This is not a code issue.",
        FailureClassification.LOGIC_CHANGE: f"The application logic has changed, requiring test logic updates. This is not a simple locator fix.",
        FailureClassification.UNKNOWN: f"Unable to classify the failure type. Manual investigation required.",
    }
    
    return explanations.get(failure_type, "Unknown root cause")


def _generate_recommendations(failure_type: FailureClassification, 
                               locator_info: Optional[LocatorInfo]) -> list[str]:
    """Generate recommendations for fixing the issue."""
    recommendations = []
    
    if failure_type == FailureClassification.LOCATOR_STALE and locator_info:
        recommendations.append("Update the selector to use role-based locator (getByRole)")
        recommendations.append("Verify the new selector with Playwright MCP before applying")
        recommendations.append("Consider using data-testid attributes for more stable selectors")
    
    elif failure_type == FailureClassification.DATA_MISMATCH:
        recommendations.append("Review test data configuration in run_context.json")
        recommendations.append("Update test data to match current application validation rules")
    
    elif failure_type == FailureClassification.TIMING_FLAKE:
        recommendations.append("Add explicit waits using Playwright's auto-waiting features")
        recommendations.append("Review test timing and add retry logic if needed")
    
    elif failure_type == FailureClassification.ENV_FAILURE:
        recommendations.append("Check environment configuration and service availability")
        recommendations.append("Verify network connectivity and external dependencies")
    
    elif failure_type == FailureClassification.LOGIC_CHANGE:
        recommendations.append("Review the application changes that caused the test to fail")
        recommendations.append("Update test logic to match new application behavior")
    
    else:
        recommendations.append("Manual investigation required to determine appropriate fix")
    
    return recommendations
