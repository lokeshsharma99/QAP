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
from agents.ci_log_analyzer import ci_log_analyzer
from agents.concierge import concierge
from agents.curator import curator
from agents.scout import scout
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
from app.endpoints.agent_config import router as agent_config_router
from app.endpoints.auth import router as auth_router
from app.endpoints.automation_health import router as automation_health_router
from app.endpoints.rtm import router as rtm_router
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
from app.tenancy_middleware import OrgScopingMiddleware
from db import get_automation_kb, get_qap_learnings_kb, get_rca_kb, get_site_manifesto_kb
from teams.context import context_team
from teams.diagnostics import diagnostics_team
from teams.engineering import engineering_team
from teams.grooming import grooming_team
from teams.intelligence import intelligence_team
from teams.operations import operations_team
from teams.strategy import strategy_team
from workflows.automation_scaffold import automation_scaffold
from workflows.ado_ci_triage import ado_ci_triage
from workflows.discovery_onboard import discovery_onboard
from workflows.full_lifecycle import full_lifecycle
from workflows.full_regression import full_regression
from workflows.grooming import grooming
from workflows.impact_assessment import impact_assessment
from workflows.jira_to_pr import jira_to_pr
from workflows.pipeline_failure_assessment import pipeline_failure_assessment
from workflows.regression_maintenance import regression_maintenance
from workflows.spec_to_code import spec_to_code
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
        ci_log_analyzer,
        impact_analyst,
        pipeline_analyst,
        healing_judge,
        scout,
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
        ado_ci_triage,
        automation_scaffold,
        full_lifecycle,
        full_regression,
        grooming,
        regression_maintenance,
    ],
    knowledge=_kb_list if _kb_list else None,
    registry=registry,
    config=str(Path(__file__).parent / "config.yaml"),
)

app = agent_os.get_app()

# ---------------------------------------------------------------------------
# Org-Scoping Middleware
# Must be added BEFORE the CORS middleware (outermost layer wins for raw ASGI
# middleware).  Intercepts Agno run endpoints and injects user_id = org_id so
# all users in the same org share memory, sessions, traces, and culture.
# Non-run endpoints (culture, optimize-memories) read org_id from
# request.state.org_id which the middleware writes to scope["state"].
# ---------------------------------------------------------------------------
app.add_middleware(OrgScopingMiddleware)  # type: ignore[arg-type]

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
# for private-network IPs (192.168.x.x, 10.x.x.x, 172.16-31.x.x) on port 3000
# and VS Code dev tunnels (*.devtunnels.ms).
_ALLOWED_ORIGIN_RE = re.compile(
    r"^https?://(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(:\d+)?$"
    r"|^https://[a-z0-9]+-\d+\.[\w]+\.devtunnels\.ms$"
    r"|^https://[a-zA-Z0-9-]+\.(ngrok-free\.dev|ngrok-free\.app|ngrok\.io|trycloudflare\.com|loca\.lt)$"
    r"|^https://[a-zA-Z0-9-]+\.azurecontainerapps\.io$"
)

# Gather the existing Agno-set origins and append ours
_existing_origins: list[str] = []
for _mw in app.user_middleware:
    if _mw.cls == CORSMiddleware:
        _existing_origins = _mw.kwargs.get("allow_origins", [])
        break

_all_origins = list({
    *_existing_origins,
    *_extra_origins,
    # Always allow the default local UI origins so the browser never gets blocked
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
})

# Remove old CORS middleware and add a new one with allow_origin_regex
app.user_middleware = [m for m in app.user_middleware if m.cls != CORSMiddleware]
app.middleware_stack = None
app.add_middleware(
    CORSMiddleware,
    allow_origins=_all_origins,
    allow_origin_regex=_ALLOWED_ORIGIN_RE.pattern,
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
app.include_router(auth_router)
app.include_router(automation_health_router)
app.include_router(rtm_router)
app.include_router(culture_router)
app.include_router(profile_router)
app.include_router(organization_router)

# ---------------------------------------------------------------------------
# Auth guard middleware
#
# Blocks anonymous access to all endpoints EXCEPT:
#   /auth/*         — login, register, accept-invite, validate-invite
#   /health         — Docker health check
#   /docs, /openapi — Swagger UI (only in dev)
#
# The RUNTIME_ENV check means: in dev mode auth is advisory (warns but passes),
# in prd mode it hard-blocks with 401.  Set RUNTIME_ENV=prd in production.
# ---------------------------------------------------------------------------
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402
from starlette.responses import JSONResponse             # noqa: E402

_AUTH_BYPASS_PREFIXES = (
    "/auth/",
    "/health",
    "/docs",
    "/openapi",
    "/redoc",
    "/favicon",
)

class AuthGuardMiddleware(BaseHTTPMiddleware):
    """Block unauthenticated requests in production mode.

    In dev mode, requests without a session token still pass but are logged
    so developers can see what would be blocked in production.
    """

    async def dispatch(self, request, call_next):
        path = request.url.path
        # Always allow auth + health + docs routes
        if any(path.startswith(p) for p in _AUTH_BYPASS_PREFIXES):
            return await call_next(request)

        authorization = request.headers.get("authorization", "")
        raw_token = authorization.removeprefix("Bearer ").strip()

        if not raw_token:
            if RUNTIME_ENV == "prd":
                return JSONResponse({"detail": "Not authenticated."}, status_code=401)
            # Dev: pass through (allows Swagger/agent-ui to work without token)
            return await call_next(request)

        # Validate the session token
        from app.endpoints.auth import _validate_session
        user = _validate_session(raw_token)
        if user is None and RUNTIME_ENV == "prd":
            return JSONResponse({"detail": "Session expired or invalid."}, status_code=401)

        return await call_next(request)


app.add_middleware(AuthGuardMiddleware)

# ---------------------------------------------------------------------------
# Automation folder watcher — event-driven KB sync
#
# Uses the `watchfiles` package (already installed via uvicorn[standard]).
# Monitors automation/ for any file changes: creates, edits, or deletes.
# On change → calls the Librarian's re_index_file() for that specific file.
# Debounced per-file: same file only re-indexed once per 5-second window.
# Runs as an asyncio background task during the FastAPI process lifetime.
# ---------------------------------------------------------------------------
import asyncio  # noqa: E402
import logging  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402

_watcher_logger = logging.getLogger("qap.watcher")
_AUTOMATION_PATH = Path(__file__).resolve().parent.parent / "automation"

_WATCH_EXTENSIONS = {".ts", ".js", ".feature", ".json"}
_debounce_cache: dict[str, float] = {}
_DEBOUNCE_SECONDS = 5.0


async def _watch_automation_dir() -> None:
    """Background coroutine: watch automation/ and re-index on every change."""
    try:
        from watchfiles import awatch, Change

        _watcher_logger.info(f"[watcher] Watching {_AUTOMATION_PATH} for changes…")
        async for changes in awatch(str(_AUTOMATION_PATH), stop_event=asyncio.Event()):
            for change_type, file_path in changes:
                # Skip files we don't index
                if Path(file_path).suffix not in _WATCH_EXTENSIONS:
                    continue
                # Skip node_modules and hidden dirs
                if "node_modules" in file_path or "/.git/" in file_path or "\\.git\\" in file_path:
                    continue

                # Debounce — don't re-index same file twice within 5 seconds
                now = asyncio.get_event_loop().time()
                last = _debounce_cache.get(file_path, 0.0)
                if now - last < _DEBOUNCE_SECONDS:
                    continue
                _debounce_cache[file_path] = now

                action = {Change.added: "added", Change.modified: "modified", Change.deleted: "deleted"}.get(change_type, "changed")
                _watcher_logger.info(f"[watcher] File {action}: {file_path}")

                # Run indexing in a thread pool so it doesn't block the event loop
                try:
                    from agents.librarian.tools import _reindex_single_file
                    await asyncio.get_event_loop().run_in_executor(
                        None, _reindex_single_file, file_path
                    )
                    _watcher_logger.info(f"[watcher] Re-indexed: {file_path}")
                    # If a POM changed, re-run the manifesto link for that file
                    if "pages/" in file_path.replace("\\", "/") and file_path.endswith(".ts"):
                        from agents.librarian.tools import link_pom_to_manifesto
                        await asyncio.get_event_loop().run_in_executor(None, link_pom_to_manifesto)
                except Exception as exc:
                    _watcher_logger.warning(f"[watcher] Re-index failed for {file_path}: {exc}")

    except ImportError:
        _watcher_logger.warning("[watcher] watchfiles not installed — file watching disabled.")
    except Exception as exc:
        _watcher_logger.error(f"[watcher] Unexpected error: {exc}")


# Register the watcher as a FastAPI startup event
@app.on_event("startup")
async def _start_watcher() -> None:
    """Start the automation/ file watcher as a background asyncio task."""
    if _AUTOMATION_PATH.exists():
        asyncio.create_task(_watch_automation_dir())
        _watcher_logger.info("[watcher] Background file watcher started.")
    else:
        _watcher_logger.warning("[watcher] automation/ dir not found — watcher not started.")


if __name__ == "__main__":
    agent_os.serve(
        app="app.main:app",
        reload=RUNTIME_ENV == "dev",
    )
