"""
Quality Autopilot
=================

The main entry point for Quality Autopilot AgentOS.

Run:
    python -m app.main
"""

from pathlib import Path

from agno.os import AgentOS

from agents.architect import architect
from agents.data_agent import data_agent
from agents.detective import detective
from agents.discovery import discovery
from agents.engineer import engineer
from agents.impact_analyst import impact_analyst
from agents.judge import judge
from agents.librarian import librarian
from agents.medic import medic
from agents.pipeline_analyst import pipeline_analyst
from agents.scribe import scribe
from app.registry import registry
from app.settings import RUNTIME_ENV, agent_db
from teams.context import context_team
from teams.engineering import engineering_team
from teams.operations import operations_team
from teams.strategy import strategy_team
from workflows.discovery_onboard import discovery_onboard
from workflows.spec_to_code import spec_to_code
from workflows.triage_heal import triage_heal

# ---------------------------------------------------------------------------
# Create AgentOS
# ---------------------------------------------------------------------------
agent_os = AgentOS(
    name="Quality Autopilot",
    tracing=True,
    authorization=RUNTIME_ENV == "prd",
    db=agent_db,
    agents=[
        discovery,
        librarian,
        architect,
        scribe,
        judge,
        engineer,
        data_agent,
        detective,
        medic,
        impact_analyst,
        pipeline_analyst,
    ],
    teams=[
        context_team,
        strategy_team,
        engineering_team,
        operations_team,
    ],
    workflows=[
        discovery_onboard,
        spec_to_code,
        triage_heal,
    ],
    registry=registry,
    config=str(Path(__file__).parent / "config.yaml"),
)

app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(
        app="app.main:app",
        reload=RUNTIME_ENV == "dev",
    )
