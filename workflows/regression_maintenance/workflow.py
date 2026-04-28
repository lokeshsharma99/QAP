"""
Regression Maintenance Workflow
================================

Workflow for regression suite curation and maintenance.
"""

from agno.workflow import Workflow, Step

from agents.curator.agent import curator
from agents.discovery.agent import discovery
from agents.librarian.agent import librarian
from workflows.regression_maintenance.instructions import INSTRUCTIONS

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
regression_maintenance = Workflow(
    id="regression_maintenance",
    name="Regression Suite Maintenance",
    steps=[
        # Step 1: Detect AUT Changes (Discovery Agent)
        Step(
            name="Detect AUT Changes",
            agent=discovery,
            description="Crawl AUT and generate current Site Manifesto",
        ),
        # Step 2: Compare Site Manifesto (Curator Agent)
        Step(
            name="Compare Site Manifesto",
            agent=curator,
            description="Compare current Site Manifesto with previous version",
        ),
        # Step 3: Identify Obsolete Tests (Curator Agent)
        Step(
            name="Identify Obsolete Tests",
            agent=curator,
            description="Use Librarian's obsolescence detection tools",
        ),
        # Step 4: Generate Deletion Recommendations (Curator Agent)
        Step(
            name="Generate Deletion Recommendations",
            agent=curator,
            description="Create TestDeletionRequest objects with justifications",
        ),
        # Step 5: HITL Approval (Curator Agent)
        Step(
            name="Request HITL Approval",
            agent=curator,
            description="Request batch approval using Agno's native approval mechanism",
        ),
        # Step 6: Execute Approved Deletions (Curator Agent)
        Step(
            name="Execute Approved Deletions",
            agent=curator,
            description="Delete approved tests with backups",
        ),
        # Step 7: Update Knowledge Base (Librarian Agent)
        Step(
            name="Update Knowledge Base",
            agent=librarian,
            description="Re-index the automation codebase",
        ),
        # Step 8: Generate Maintenance Report (Curator Agent)
        Step(
            name="Generate Maintenance Report",
            agent=curator,
            description="Create ObsolescenceReport and save to disk",
        ),
    ],
)
