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
from agents.curator import curator
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
from app.endpoints.agent_config import router as agent_config_router
from app.endpoints.model import router as model_router
from app.endpoints.optimize_memories import router as optimize_memories_router
from app.endpoints.settings import router as settings_router
from app.registry import registry
from app.settings import RUNTIME_ENV, agent_db
from teams.context import context_team
from teams.diagnostics import diagnostics_team
from teams.engineering import engineering_team
from teams.grooming import grooming_team
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
    scheduler=True,
    scheduler_poll_interval=15,
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
        curator,
        impact_analyst,
        pipeline_analyst,
    ],
    teams=[
        context_team,
        strategy_team,
        engineering_team,
        operations_team,
        diagnostics_team,
        grooming_team,
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

# ---------------------------------------------------------------------------
# Override /optimize-memories to use MODEL (kilo-auto/free) instead of gpt-4o.
# Insert before agno routes so FastAPI's first-match wins.
# ---------------------------------------------------------------------------
from fastapi.routing import APIRoute  # noqa: E402

app.include_router(optimize_memories_router)
# Move our override to the front of the route list so it takes priority
new_routes = [r for r in app.routes if isinstance(r, APIRoute) and r.path == "/optimize-memories"
              and r.operation_id == "optimize_memories_kilo"]
other_routes = [r for r in app.routes if r not in new_routes]
app.routes.clear()
app.routes.extend(new_routes + other_routes)

app.include_router(settings_router)
app.include_router(model_router)
app.include_router(agent_config_router)

if __name__ == "__main__":
    agent_os.serve(
        app="app.main:app",
        reload=RUNTIME_ENV == "dev",
    )
