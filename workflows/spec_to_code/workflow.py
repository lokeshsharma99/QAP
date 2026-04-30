"""
Spec-to-Code Workflow
=====================

Requirement (Jira) → Architect → Scribe → [Judge Gate] → Data Agent → Engineer → PR

Pipeline:
  1. Parse Requirements (Architect)
  2. Author Gherkin (Scribe)
  3. Gherkin Judge Gate (Condition)
  4. Provision Data (Data Agent)
  5. Generate Code (Engineer)
  6. Code Judge Gate (Condition)
"""

import re

from agno.workflow import Condition, Step, Workflow

from agents.architect import architect
from agents.data_agent import data_agent
from agents.engineer import engineer
from agents.judge import judge
from agents.scribe import scribe
from contracts.workflow_inputs import JiraTicketInput


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def gherkin_lint_passes(step_input) -> bool:  # type: ignore[no-untyped-def]
    """Gate: only proceed if Gherkin spec contains valid structure."""
    content = str(getattr(step_input, "previous_step_content", "") or "")
    return "Feature:" in content and "Scenario:" in content


def code_quality_passes(step_input) -> bool:  # type: ignore[no-untyped-def]
    """Gate: only proceed if code has no hardcoded sleeps."""
    content = str(getattr(step_input, "previous_step_content", "") or "")
    has_sleep = bool(re.search(r"sleep\(|waitForTimeout\(", content))
    has_class = bool(re.search(r"class\s+\w+Page", content))
    return has_class and not has_sleep


# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
spec_to_code = Workflow(
    id="spec-to-code",
    name="Spec to Code Pipeline",
    description="Requirement → Architect → Scribe → [Gherkin Judge Gate] → Data Agent → Engineer → PR",
    input_schema=JiraTicketInput,
    steps=[
        Step(name="Parse Requirements", agent=architect),
        Step(name="Author Gherkin", agent=scribe),
        Condition(
            name="Gherkin Judge Gate",
            evaluator=gherkin_lint_passes,
            steps=[
                Step(name="Provision Data", agent=data_agent),
                Step(name="Generate Code", agent=engineer),
                Condition(
                    name="Code Judge Gate",
                    evaluator=code_quality_passes,
                    steps=[
                        Step(name="Final Review", agent=judge),
                    ],
                ),
            ],
        ),
    ],
)
