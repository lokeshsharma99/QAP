"""
Spec-to-Code Workflow
=====================

Workflow for converting Gherkin specifications to Playwright automation code.
End-to-end orchestration of spec → code → execute → triage → heal cycle.
"""

from agno.workflow import Workflow, Step

from agents.data_agent import data_agent
from agents.engineer import engineer
from agents.judge import judge
from teams.engineering import engineering_team

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
spec_to_code = Workflow(
    id="spec-to-code",
    name="Spec to Code",
    steps=[
        Step(
            name="Parse Feature File",
            agent=engineer,
            description="Parse the .feature file and extract test scenarios",
        ),
        Step(
            name="Provision Test Data",
            agent=data_agent,
            description="Generate run_context.json with test data and PII masking",
        ),
        Step(
            name="Generate Page Objects",
            agent=engineer,
            description="Generate modular POM classes using Look-Before-You-Leap pattern",
        ),
        Step(
            name="Generate Step Definitions",
            agent=engineer,
            description="Generate step definitions for the test scenarios",
        ),
        Step(
            name="Code Quality Gate",
            agent=judge,
            description="Validate generated code: eslint, type-check, no hardcoded sleeps",
        ),
        Step(
            name="Local Verification",
            agent=engineer,
            description="Run local containerized execution to ensure green run",
        ),
        Step(
            name="Create Pull Request",
            agent=engineer,
            description="Create GitHub branch and draft PR for code review",
        ),
    ],
)
