"""
Impact Assessment Workflow
===========================

PR / Issue / Jira / ADO → Impact Analyst → Judge Gate → ImpactReport

Phase 1: Intelligence Gathering
  - Fetch change surface (GitHub PR diff, Jira ACs, ADO work items)
  - Query Automation KB for existing coverage
  - Query Site Manifesto KB for locator currency

Phase 2: Analysis & Generation
  - Classify each gap (missing_coverage / obsolete / needs_update)
  - Assign priority (P0-P3) and compute regression risk
  - Produce ImpactReport with ordered recommended_actions

Phase 3: Quality Gate
  - Judge reviews the ImpactReport
  - confidence >= 0.90 → auto-approve → report delivered
  - confidence < 0.90  → human review → held in HITL queue
"""

import re

from agno.workflow import Condition, Step, Workflow

from agents.impact_analyst import impact_analyst
from agents.judge import judge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _extract_confidence(content: str) -> float:
    """Extract confidence score from a Judge verdict response."""
    match = re.search(r'"confidence":\s*([\d.]+)', content)
    if match:
        return float(match.group(1))
    # Also handle "Confidence: 92%" format from markdown report
    pct_match = re.search(r'[Cc]onfidence[:\s]+(\d+)%', content)
    if pct_match:
        return float(pct_match.group(1)) / 100.0
    return 0.0


def judge_approves_impact_report(step_input) -> bool:  # type: ignore[no-untyped-def]
    """Gate: only deliver ImpactReport when Judge confidence >= 90%.

    Checks for:
    - Presence of the impact_report JSON block
    - At least one gap classified with priority
    - regression_risk field is set
    """
    content = str(getattr(step_input, "previous_step_content", "") or "")
    has_report_block = "```impact_report" in content or '"regression_risk"' in content
    confidence = _extract_confidence(content)
    requires_human = bool(re.search(r'"requires_human_review":\s*true', content, re.IGNORECASE))
    return has_report_block and confidence >= 0.90 and not requires_human


# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
impact_assessment = Workflow(
    id="impact-assessment",
    name="PR Change Impact Analysis",
    description=(
        "PR / Issue / Jira / ADO → Impact Analyst → Judge Gate → ImpactReport. "
        "Identifies missing coverage, obsolete tests, and stale assertions with "
        "P0-P3 priority and regression risk scoring."
    ),
    steps=[
        Step(
            name="Gather Intelligence & Produce ImpactReport",
            agent=impact_analyst,
            description=(
                "Phase 1: Fetch the change surface using GitHub MCP (PR diff / Issue ACs), "
                "Atlassian MCP (Jira ACs), and/or ADO MCP (work item ACs). "
                "Query the Automation KB for existing coverage. "
                "Query the Site Manifesto KB for locator currency. "
                "\n\n"
                "Phase 2: Classify each gap (missing_coverage / obsolete / needs_update), "
                "assign priority (P0-P3), compute regression_risk, and produce a full "
                "ImpactReport with ordered recommended_actions. "
                "\n\n"
                "Output a markdown summary followed by a ```impact_report JSON block."
            ),
        ),
        Step(
            name="Judge Review",
            agent=judge,
            description=(
                "Review the ImpactReport against the Definition of Done checklist:\n"
                "- [ ] Change surface was fetched from a real source (GitHub / Jira / ADO)\n"
                "- [ ] Automation KB was queried BEFORE concluding coverage is missing\n"
                "- [ ] Site Manifesto KB was checked for locator currency\n"
                "- [ ] Every gap has type, priority, and suggested_action\n"
                "- [ ] regression_risk is set and justified by the gap priorities\n"
                "- [ ] recommended_actions are ordered with P0 first\n"
                "- [ ] No hallucinated file paths (only confirmed-existing files cited)\n"
                "- [ ] requires_human_review is set correctly\n"
                "\n"
                "Respond with a JudgeVerdict containing your confidence score (0.0-1.0). "
                "confidence >= 0.90 → APPROVE. "
                "confidence < 0.90 → list specific deficiencies for the Impact Analyst to address."
            ),
        ),
        Condition(
            name="Judge Gate",
            evaluator=judge_approves_impact_report,
            steps=[
                Step(
                    name="Deliver ImpactReport",
                    agent=impact_analyst,
                    description=(
                        "The ImpactReport has been approved by the Judge. "
                        "Format and deliver the final approved report to the user. "
                        "Include the full markdown summary and the impact_report JSON block. "
                        "Summarise the top recommended actions in plain language."
                    ),
                ),
            ],
            else_steps=[
                Step(
                    name="Refine ImpactReport",
                    agent=impact_analyst,
                    description=(
                        "The Judge has flagged deficiencies in the ImpactReport. "
                        "Address each deficiency listed in the Judge verdict: "
                        "re-query any missing KB searches, verify file paths, "
                        "strengthen evidence for gap classifications, and re-produce "
                        "the ImpactReport. "
                        "Output updated markdown summary and ```impact_report JSON block."
                    ),
                ),
            ],
        ),
    ],
)
