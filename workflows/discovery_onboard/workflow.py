"""
Discovery Onboard Workflow
==========================

AUT URL → Discovery Agent → Site Manifesto → Vectorized KB.

Usage:
    from workflows.discovery_onboard import discovery_onboard
    discovery_onboard.run("Crawl https://gds-demo-app.vercel.app/")
"""

from agno.workflow import Step, Workflow

from agents.discovery import discovery
from agents.librarian import librarian

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
discovery_onboard = Workflow(
    id="discovery-onboard",
    name="AUT Onboarding",
    description="AUT URL → Discovery (Site Manifesto) → Librarian (index automation codebase) → Vectorized KB",
    steps=[
        Step(name="Crawl AUT", agent=discovery),
        # After Discovery writes the Site Manifesto to PgVector,
        # Librarian indexes the full automation/ codebase so the KB is
        # immediately ready for Engineer's Look-Before-You-Leap queries.
        Step(
            name="Index Automation Codebase",
            agent=librarian,
            description="""As the Librarian, index the full automation/ codebase into the automation_kb.

Input: Site Manifesto from the Discovery step (available in shared context).

Your task:
1. Walk automation/pages/ and index every .ts POM file.
2. Walk automation/step_definitions/ and index every .ts step file.
3. Walk automation/features/ and index every .feature file.
4. Add a learning to qap_learnings_kb summarising the AUT structure
   and the number of pages/components discovered.

Output: Confirmation of files indexed and KB size.""",
        ),
    ],
)
