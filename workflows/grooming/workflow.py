"""
Grooming Workflow
================

Workflow for 3 Amigos user story review from BA, SDET, and Dev perspectives.
"""

from agno.workflow import Workflow, Step

from agents.architect import architect
from agents.judge import judge
from teams.grooming import grooming_team

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
grooming = Workflow(
    id="grooming",
    name="3 Amigos Grooming",
    steps=[
        Step(
            name="BA Assessment",
            agent=architect,
            description="Evaluate testability and completeness from BA perspective",
        ),
        Step(
            name="SDET Assessment",
            agent=judge,
            description="Evaluate automation feasibility, edge cases, and risk from SDET perspective",
        ),
        Step(
            name="Synthesize Assessment",
            agent=judge,
            description="Combine all perspectives into GroomingAssessment",
        ),
        Step(
            name="Post to Jira",
            agent=architect,
            description="Add assessment as comment to Jira ticket",
        ),
    ],
)
