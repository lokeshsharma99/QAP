"""
Triage-Heal Workflow
====================

Workflow for converting test failures into automated healing.
End-to-end orchestration of failure → RCA → healing → verification cycle.
"""

from agno.workflow import Workflow, Step

from agents.detective import detective
from agents.engineer import engineer
from agents.healing_judge import healing_judge
from agents.librarian import librarian
from agents.medic import medic
from teams.operations import operations_team

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
triage_heal = Workflow(
    id="triage-heal",
    name="Triage and Heal",
    steps=[
        Step(
            name="Analyze Failure",
            agent=detective,
            description="Analyze trace.zip to identify root cause and generate RCAReport",
        ),
        Step(
            name="Assess Healability",
            agent=detective,
            description="Determine if failure is healable (LOCATOR_STALE with high confidence)",
        ),
        Step(
            name="Generate Healing Patch",
            agent=medic,
            description="Create surgical edit if healable, otherwise escalate to human",
        ),
        Step(
            name="Validate Healing Patch",
            agent=healing_judge,
            description="Validate patch is surgical (confidence ≥90%, no logic changes, proper locator strategy)",
        ),
        Step(
            name="Apply Healing Patch",
            agent=medic,
            description="Apply the healing patch to automation code",
        ),
        Step(
            name="Verify Healing (3x)",
            agent=medic,
            description="Run test verification 3 times to confirm fix stability",
        ),
        Step(
            name="Update Knowledge Base",
            agent=librarian,
            description="Store healing learnings in knowledge base for future reference",
        ),
    ],
)
