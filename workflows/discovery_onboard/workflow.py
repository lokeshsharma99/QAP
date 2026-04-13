"""
Discovery Onboard Workflow
==========================

Workflow for automating AUT onboarding and knowledge base population.
End-to-end orchestration of AUT URL → Discovery → Manifesto → Librarian → KB.
"""

from agno.workflow import Workflow, Step

from agents.discovery import discovery
from agents.librarian import librarian

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
discovery_onboard = Workflow(
    id="discovery-onboard",
    name="Discovery Onboard",
    steps=[
        Step(
            name="Crawl AUT",
            agent=discovery,
            description="Crawl the AUT URL to extract UI elements and generate Site Manifesto",
        ),
        Step(
            name="Index Site Manifesto",
            agent=librarian,
            description="Index the Site Manifesto into the knowledge base",
        ),
        Step(
            name="Index Codebase",
            agent=librarian,
            description="Index the automation codebase into the knowledge base",
        ),
        Step(
            name="Verify Knowledge Base",
            agent=librarian,
            description="Verify the knowledge base is searchable and contains relevant information",
        ),
    ],
)
