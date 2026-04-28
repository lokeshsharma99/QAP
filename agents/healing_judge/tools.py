"""
Healing Judge Tools
====================

Custom tools for the Healing Judge Agent to validate surgical edits.
"""

from agno.tools.toolkit import Toolkit


def validate_surgical_edit(file_path: str, old_locator: str, new_locator: str) -> dict:
    """Verify the edit is selector-only (no logic changes).

    Args:
        file_path: Path to the file being edited
        old_locator: The old locator being replaced
        new_locator: The new locator to apply

    Returns:
        Dictionary with validation results (is_surgical, issues)
    """
    issues = []
    
    # Check if the edit is changing a selector only
    # A surgical edit should only change locator strings
    if old_locator == new_locator:
        issues.append("Old and new locators are identical - no change needed")
    
    # Check if the change is purely selector-based (not logic)
    # This is a simplified check - in practice would parse the file
    if "assert" in new_locator.lower() or "expect" in new_locator.lower():
        issues.append("New locator contains assertion keywords - possible logic change")
    
    if "if " in new_locator.lower() or "for " in new_locator.lower():
        issues.append("New locator contains control flow keywords - possible logic change")
    
    return {
        "is_surgical": len(issues) == 0,
        "issues": issues,
    }


def check_locator_strategy(locator: str) -> dict:
    """Verify locator compliance (data-testid, role, or text strategies).

    Args:
        locator: The locator string to validate

    Returns:
        Dictionary with compliance results (is_compliant, strategy_used, issues)
    """
    issues = []
    strategy_used = "unknown"
    
    # Check for data-testid strategy
    if 'data-testid' in locator or 'getByTestId' in locator:
        strategy_used = "data-testid"
    # Check for role strategy
    elif 'getByRole' in locator or 'role=' in locator:
        strategy_used = "role"
    # Check for text strategy
    elif 'getByText' in locator or 'text=' in locator:
        strategy_used = "text"
    # Check for CSS selector ( discouraged but allowed)
    elif 'getBySelector' in locator or '.' in locator or '#' in locator:
        strategy_used = "css_selector"
        issues.append("CSS selector strategy is discouraged - prefer data-testid, role, or text")
    # Check for XPath ( strongly discouraged)
    elif 'getByXPath' in locator or 'xpath' in locator.lower():
        strategy_used = "xpath"
        issues.append("XPath strategy is strongly discouraged - use data-testid, role, or text")
    else:
        issues.append("Unable to determine locator strategy")
    
    return {
        "is_compliant": strategy_used in ["data-testid", "role", "text"],
        "strategy_used": strategy_used,
        "issues": issues,
    }


def check_no_hardcoded_values(locator: str) -> dict:
    """Detect new hardcoding in locators.

    Args:
        locator: The locator string to check

    Returns:
        Dictionary with hardcoding analysis (has_hardcoded_values, issues)
    """
    issues = []
    
    # Check for common hardcoded patterns
    # This is a simplified check - in practice would be more sophisticated
    if '"' in locator and '{' not in locator:
        # Might have hard-coded values instead of parameters
        if not any(kw in locator for kw in ['data-testid', 'getByRole', 'getByText']):
            issues.append("Possible hardcoded value detected - consider using parameters")
    
    # Check for numeric IDs (often hardcoded)
    import re
    if re.search(r'\b\d{3,}\b', locator) and 'data-testid' not in locator:
        issues.append("Possible hardcoded numeric ID detected")
    
    return {
        "has_hardcoded_values": len(issues) > 0,
        "issues": issues,
    }


def validate_healing_patch(healing_patch: dict) -> dict:
    """Comprehensive validation of a HealingPatch.

    Args:
        healing_patch: The HealingPatch object as a dictionary

    Returns:
        Dictionary with comprehensive validation results
    """
    from contracts.healing_patch import HealingPatch
    
    # Convert dict to Pydantic model for validation
    try:
        patch = HealingPatch(**healing_patch)
        validation_errors = []
        
        # Validate surgical edit
        surgical_result = validate_surgical_edit(
            patch.file_path,
            patch.old_locator,
            patch.new_locator
        )
        if not surgical_result["is_surgical"]:
            validation_errors.extend(surgical_result["issues"])
        
        # Validate locator strategy
        strategy_result = check_locator_strategy(patch.new_locator)
        if not strategy_result["is_compliant"]:
            validation_errors.extend(strategy_result["issues"])
        
        # Validate no hardcoded values
        hardcoding_result = check_no_hardcoded_values(patch.new_locator)
        if hardcoding_result["has_hardcoded_values"]:
            validation_errors.extend(hardcoding_result["issues"])
        
        # Calculate confidence score
        confidence = calculate_confidence({
            "valid": len(validation_errors) == 0,
            "surgical_check": surgical_result,
            "strategy_check": strategy_result,
            "hardcoding_check": hardcoding_result,
        })
        
        return {
            "valid": len(validation_errors) == 0,
            "validation_errors": validation_errors,
            "surgical_check": surgical_result,
            "strategy_check": strategy_result,
            "hardcoding_check": hardcoding_result,
            "confidence": confidence,
        }
    except Exception as e:
        return {
            "valid": False,
            "validation_errors": [f"Validation error: {str(e)}"],
            "surgical_check": None,
            "strategy_check": None,
            "hardcoding_check": None,
            "confidence": 0.0,
        }


def calculate_confidence(validation_results: dict) -> float:
    """Calculate confidence score from validation results.

    Args:
        validation_results: Dictionary with validation check results

    Returns:
        Confidence score between 0.0 and 100.0
    """
    base = 100.0
    
    # Deduct points for failed validations
    if not validation_results.get("valid", False):
        base -= 50.0
    
    surgical_check = validation_results.get("surgical_check", {})
    if surgical_check and not surgical_check.get("is_surgical", False):
        base -= 20.0
    
    strategy_check = validation_results.get("strategy_check", {})
    if strategy_check and not strategy_check.get("is_compliant", False):
        base -= 15.0
    
    hardcoding_check = validation_results.get("hardcoding_check", {})
    if hardcoding_check and hardcoding_check.get("has_hardcoded_values", False):
        base -= 15.0
    
    return max(base, 0.0)


# Create toolkit for Healing Judge Agent
healing_judge_tools = Toolkit(
    tools=[
        validate_surgical_edit,
        check_locator_strategy,
        check_no_hardcoded_values,
        validate_healing_patch,
        calculate_confidence,
    ]
)
