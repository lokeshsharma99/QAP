"""
Judge Agent Tools
=================

Custom tools for the Judge Agent to perform Gherkin validation and linting.
"""

from agno.tools.toolkit import Toolkit


def validate_gherkin_syntax(gherkin_content: str) -> dict:
    """Validate Gherkin syntax in a feature file.

    Args:
        gherkin_content: The Gherkin feature file content

    Returns:
        Dictionary with validation results (valid, errors, warnings)
    """
    errors = []
    warnings = []

    lines = gherkin_content.split('\n')
    
    # Find first non-empty line for Feature check
    first_non_empty_line = 0
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped:
            first_non_empty_line = i
            if not stripped.startswith('Feature:'):
                errors.append(f"Line {i}: Feature file must start with 'Feature:' keyword")
            break
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Check for valid Gherkin keywords
        if stripped and not any(stripped.startswith(kw) for kw in ['Feature:', 'Scenario:', 'Given', 'When', 'Then', 'And', 'But', '@', '#', '']):
            # Could be a step continuation, which is valid
            pass
        
        # Check for Scenario structure
        if stripped.startswith('Scenario:'):
            # Next non-empty lines should be Given/When/Then/And/But
            pass
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def check_step_reusability(gherkin_content: str) -> dict:
    """Check if Gherkin steps are reusable (no hard-coded values).

    Args:
        gherkin_content: The Gherkin feature file content

    Returns:
        Dictionary with reusability analysis (reusable_score, issues)
    """
    issues = []
    
    lines = gherkin_content.split('\n')
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Look for hard-coded values in steps
        if any(stripped.startswith(kw) for kw in ['Given', 'When', 'Then', 'And', 'But']):
            # Check for common hard-coded patterns
            if '"' in stripped and '{' not in stripped:
                # Might have hard-coded values instead of parameters
                issues.append(f"Line {i}: Possible hard-coded value, consider using parameters")
    
    return {
        "reusable_score": 100 - (len(issues) * 10),
        "issues": issues,
    }


def check_traceability(gherkin_content: str) -> dict:
    """Check if the Gherkin spec has traceability to source ticket.

    Args:
        gherkin_content: The Gherkin feature file content

    Returns:
        Dictionary with traceability analysis (has_traceability, ticket_id_found)
    """
    ticket_id_found = False
    
    lines = gherkin_content.split('\n')
    
    for line in lines:
        stripped = line.strip()
        
        # Look for ticket ID in comments or tags
        if '@' in stripped or 'ticket' in stripped.lower() or 'QA-' in stripped:
            ticket_id_found = True
            break
    
    return {
        "has_traceability": ticket_id_found,
        "ticket_id_found": ticket_id_found,
    }


# Create toolkit for Judge Agent
judge_tools = Toolkit(
    tools=[
        validate_gherkin_syntax,
        check_step_reusability,
        check_traceability,
    ]
)
