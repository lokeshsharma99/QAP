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
from agents.concierge import concierge
from agents.curator import curator
from agents.data_agent import data_agent
from agents.detective import detective
from agents.discovery import discovery
from agents.engineer import engineer
from agents.healing_judge import healing_judge
from agents.impact_analyst import impact_analyst
from agents.judge import judge
from agents.librarian import librarian
from agents.medic import medic
from agents.pipeline_analyst import pipeline_analyst
from agents.scribe import scribe
from agents.technical_tester import technical_tester
from app.endpoints.agent_config import router as agent_config_router
from app.endpoints.automation_health import router as automation_health_router
from app.endpoints.culture import router as culture_router
from app.endpoints.model import router as model_router
from app.endpoints.eval_runs import router as eval_runs_router
from app.endpoints.mcp_status import router as mcp_status_router
from app.endpoints.optimize_memories import router as optimize_memories_router
from app.endpoints.organization import router as organization_router
from app.endpoints.profile import router as profile_router
from app.endpoints.settings import router as settings_router
from app.registry import registry
from app.settings import RUNTIME_ENV, agent_db
from db import get_automation_kb, get_qap_learnings_kb, get_rca_kb, get_site_manifesto_kb
from teams.context import context_team
from teams.diagnostics import diagnostics_team
from teams.engineering import engineering_team
from teams.grooming import grooming_team
from teams.intelligence import intelligence_team
from teams.operations import operations_team
from teams.strategy import strategy_team
from workflows.automation_scaffold import automation_scaffold
from workflows.discovery_onboard import discovery_onboard
from workflows.full_lifecycle import full_lifecycle
from workflows.full_regression import full_regression
from workflows.grooming import grooming
from workflows.impact_assessment import impact_assessment
from workflows.jira_to_pr import jira_to_pr
from workflows.pipeline_failure_assessment import pipeline_failure_assessment
from workflows.regression_maintenance import regression_maintenance
from workflows.spec_to_code import spec_to_code
from workflows.technical_testing import technical_testing
from workflows.triage_heal import triage_heal

# ---------------------------------------------------------------------------
# Knowledge bases — passed directly to AgentOS so they are browsable in the
# /knowledge UI page without requiring an active agent session.
# ---------------------------------------------------------------------------
_kb_list = []
for _kb_factory in [get_qap_learnings_kb, get_automation_kb, get_site_manifesto_kb, get_rca_kb]:
    try:
        _kb_list.append(_kb_factory())
    except Exception:
        pass

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
    # run_hooks_in_background: post-hooks (logging, telemetry) run as FastAPI
    # background tasks so they never block the streaming response to the UI.
    # Guardrails in pre_hooks are always synchronous regardless of this flag.
    run_hooks_in_background=True,
    agents=[
        concierge,
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
        healing_judge,
        technical_tester,
    ],
    teams=[
        context_team,
        strategy_team,
        engineering_team,
        operations_team,
        diagnostics_team,
        grooming_team,
        intelligence_team,
    ],
    workflows=[
        discovery_onboard,
        jira_to_pr,
        spec_to_code,
        triage_heal,
        impact_assessment,
        pipeline_failure_assessment,
        automation_scaffold,
        full_lifecycle,
        full_regression,
        grooming,
        regression_maintenance,
        technical_testing,
    ],
    knowledge=_kb_list if _kb_list else None,
    registry=registry,
    config=str(Path(__file__).parent / "config.yaml"),
)

app = agent_os.get_app()

# ---------------------------------------------------------------------------
# Expand CORS to allow LAN / IP-based origins.
# Agno only adds localhost:3000 by default. We inject any origins from the
# EXTRA_CORS_ORIGINS env var (comma-separated) plus a catch-all regex that
# allows http://<any-private-IP>:3000 so the UI works over the local network.
# ---------------------------------------------------------------------------
import re  # noqa: E402
from os import getenv  # noqa: E402

from starlette.middleware.cors import CORSMiddleware  # noqa: E402

_extra_origins: list[str] = [
    o.strip() for o in getenv("EXTRA_CORS_ORIGINS", "").split(",") if o.strip()
]

# Replace the CORS middleware with one that also allows wildcard-regex matching
# for private-network IPs (192.168.x.x, 10.x.x.x, 172.16-31.x.x) on port 3000.
_PRIVATE_IP_RE = re.compile(
    r"^http://(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(:\d+)?$"
)

# Gather the existing Agno-set origins and append ours
_existing_origins: list[str] = []
for _mw in app.user_middleware:
    if _mw.cls == CORSMiddleware:
        _existing_origins = _mw.kwargs.get("allow_origins", [])
        break

_all_origins = list({*_existing_origins, *_extra_origins})

# Remove old CORS middleware and add a new one with allow_origin_regex
app.user_middleware = [m for m in app.user_middleware if m.cls != CORSMiddleware]
app.middleware_stack = None
app.add_middleware(
    CORSMiddleware,
    allow_origins=_all_origins,
    allow_origin_regex=_PRIVATE_IP_RE.pattern,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

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

app.include_router(eval_runs_router)
# Explicitly remove Agno's built-in /eval-runs handler (operation_id="run_eval")
# so only our kilo override (operation_id="run_eval_kilo") is matched.
app.routes[:] = [
    r for r in app.routes
    if not (isinstance(r, APIRoute) and r.path == "/eval-runs"
            and getattr(r, "operation_id", None) == "run_eval")
]

app.include_router(settings_router)
app.include_router(model_router)
app.include_router(mcp_status_router)
app.include_router(agent_config_router)
app.include_router(automation_health_router)
app.include_router(culture_router)
app.include_router(profile_router)
app.include_router(organization_router)

if __name__ == "__main__":
    agent_os.serve(
        app="app.main:app",
        reload=RUNTIME_ENV == "dev",
    )
