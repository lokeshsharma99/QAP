"""
Judge Agent Tools
=================

Custom tools for the Judge Agent to perform Gherkin validation and linting.
Includes Semantica decision intelligence for tracking and learning from decisions.
"""

from agno.tools.toolkit import Toolkit
from datetime import datetime


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


def record_judge_decision(
    category: str,
    scenario: str,
    reasoning: str,
    outcome: str,
    confidence: float,
    artifact_type: str,
    artifact_id: str,
    metadata: dict = None
) -> dict:
    """
    Record a Judge decision using Semantica decision intelligence.
    
    Args:
        category: Decision category (e.g., "gherkin_approval", "code_approval")
        scenario: Decision scenario description
        reasoning: Decision reasoning and explanation
        outcome: Decision outcome (approved/rejected)
        confidence: Confidence score (0-1)
        artifact_type: Type of artifact reviewed (feature_file, code, etc.)
        artifact_id: ID of the artifact reviewed
        metadata: Additional decision metadata
    
    Returns:
        Dictionary with decision_id and status
    """
    try:
        from app.semantica_context import get_judge_context
        
        context = get_judge_context()
        
        # Build entities list for decision
        entities = [artifact_type, artifact_id]
        if metadata:
            entities.extend(metadata.keys())
        
        # Record decision with Semantica
        decision_id = context.record_decision(
            category=category,
            scenario=scenario,
            reasoning=reasoning,
            outcome=outcome,
            confidence=confidence,
            entities=entities,
            metadata={
                "artifact_type": artifact_type,
                "artifact_id": artifact_id,
                "timestamp": datetime.now().isoformat(),
                **(metadata or {})
            }
        )
        
        return {
            "decision_id": decision_id,
            "status": "recorded",
            "message": f"Decision recorded successfully with ID: {decision_id}"
        }
    except Exception as e:
        return {
            "decision_id": None,
            "status": "error",
            "message": f"Failed to record decision: {str(e)}"
        }


def find_judge_precedents(
    scenario: str,
    category: str = None,
    limit: int = 5
) -> dict:
    """
    Find similar past decisions using Semantica precedent search.
    
    Args:
        scenario: Current decision scenario to find precedents for
        category: Optional decision category filter
        limit: Maximum number of precedents to return
    
    Returns:
        Dictionary with precedent decisions and analysis
    """
    try:
        from app.semantica_context import get_judge_context
        
        context = get_judge_context()
        
        # Find precedents
        precedents = context.find_precedents_by_scenario(
            scenario=scenario,
            category=category,
            limit=limit
        )
        
        return {
            "precedents": precedents,
            "count": len(precedents),
            "status": "success"
        }
    except Exception as e:
        return {
            "precedents": [],
            "count": 0,
            "status": "error",
            "message": f"Failed to find precedents: {str(e)}"
        }


def analyze_decision_impact(decision_id: str) -> dict:
    """
    Analyze the impact of a decision using Semantica causal chain analysis.
    
    Args:
        decision_id: ID of the decision to analyze
    
    Returns:
        Dictionary with impact analysis results
    """
    try:
        from app.semantica_context import get_judge_context
        
        context = get_judge_context()
        
        # Analyze decision impact
        impact = context.graph_builder.analyze_decision_impact(decision_id)
        
        return {
            "decision_id": decision_id,
            "impact": impact,
            "status": "success"
        }
    except Exception as e:
        return {
            "decision_id": decision_id,
            "impact": None,
            "status": "error",
            "message": f"Failed to analyze impact: {str(e)}"
        }


def get_decision_insights() -> dict:
    """
    Get comprehensive insights about Judge's decision patterns using Semantica analytics.
    
    Returns:
        Dictionary with decision analytics and insights
    """
    try:
        from app.semantica_context import get_judge_context
        
        context = get_judge_context()
        
        # Get context insights
        insights = context.get_context_insights()
        
        return {
            "insights": insights,
            "status": "success"
        }
    except Exception as e:
        return {
            "insights": None,
            "status": "error",
            "message": f"Failed to get insights: {str(e)}"
        }


# Create toolkit for Judge Agent
judge_tools = Toolkit(
    tools=[
        validate_gherkin_syntax,
        check_step_reusability,
        check_traceability,
        record_judge_decision,
        find_judge_precedents,
        analyze_decision_impact,
        get_decision_insights,
    ]
)
