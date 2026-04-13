"""
Full Regression Workflow
=========================

Workflow for end-to-end regression testing orchestration.
Full pipeline: spec → code → execute → triage → heal cycle.
"""

from agno.workflow import Workflow, Step

from agents.detective import detective
from agents.engineer import engineer
from agents.healing_judge import healing_judge
from agents.librarian import librarian
from agents.medic import medic

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
full_regression = Workflow(
    id="full-regression",
    name="Full Regression",
    steps=[
        Step(
            name="Generate Automation",
            agent=engineer,
            description="Generate automation code from requirements",
        ),
        Step(
            name="Execute Tests",
            agent=engineer,
            description="Run generated tests and collect results",
        ),
        Step(
            name="Analyze Failures",
            agent=detective,
            description="Analyze test failures and generate RCA reports",
        ),
        Step(
            name="Generate Healing Patch",
            agent=medic,
            description="Create surgical edit if healable",
        ),
        Step(
            name="Validate Healing Patch",
            agent=healing_judge,
            description="Validate patch is surgical",
        ),
        Step(
            name="Verify Healing",
            agent=medic,
            description="Verify tests pass after healing",
        ),
        Step(
            name="Update Knowledge Base",
            agent=librarian,
            description="Update knowledge base with new learnings",
        ),
    ],
)
