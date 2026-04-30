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
from contracts.workflow_inputs import DiscoveryInput

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
discovery_onboard = Workflow(
    id="discovery-onboard",
    name="Discovery Onboard",
    description="AUT URL → Discovery Agent → Site Manifesto → Vectorized KB",
    input_schema=DiscoveryInput,
    steps=[
        Step(name="Crawl AUT", agent=discovery),
    ],
)
