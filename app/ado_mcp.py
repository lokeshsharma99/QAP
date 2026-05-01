"""
app/ado_mcp.py
==============

Factory functions returning Agno MCPTools instances wired to the official
Azure DevOps MCP server (@azure-devops/mcp).

The server is invoked via `npx` (stdio transport) — no separate container
needed.  Authentication uses AZURE_DEVOPS_PAT (or AZURE_DEVOPS_EXT_PAT) from
the environment; PAT-based auth is non-interactive / headless.

ADO MCP Domains (controlled via -d flag):
  core              — projects, teams, process metadata
  work              — boards, sprints, iterations
  work-items        — create / read / update / list work items
  pipelines         — pipeline runs, builds, job logs, artifacts
  repositories      — repos, branches, PRs, commits, diffs
  test-plans        — test plans, test runs, test cases, test results
  wiki              — wiki pages (read / create / update)
  search            — cross-project code and work-item search
  advanced-security — code scanning alerts (GHAzDO)

Always include "core" so the model can discover available projects.

AUT Azure DevOps resources are read from environment:
  AZURE_DEVOPS_URL     — https://dev.azure.com/<org>  or  https://<org>.visualstudio.com
  AZURE_DEVOPS_PAT     — Personal Access Token (headless auth)
  AZURE_DEVOPS_PROJECT — default project name (optional context)

Usage by agent
--------------
  Pipeline Analyst  — core, pipelines, repositories  (CI failure RCA)
  CI Log Analyzer   — core, pipelines, work-items    (logs + ticket creation)
  Architect         — core, work-items               (ADO work items as requirements)
"""

import base64
import logging
import os
import socket
import urllib.parse

from agno.utils.log import log_warning
from agno.tools.mcp import MCPTools
from mcp.client.stdio import StdioServerParameters

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ado_mcp_service_reachable(url: str) -> bool:
    """Return True if the ado-mcp Docker service TCP port is open."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or "ado-mcp"
    port = parsed.port or 8932
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def _extract_ado_org(url: str) -> str:
    """
    Extract the ADO organisation name from a full URL.

    Handles both modern (dev.azure.com) and legacy (visualstudio.com) formats.
    Falls back to returning the raw value if neither format matches so that
    callers can also pass the org name directly.
    """
    url = url.rstrip("/")
    if "dev.azure.com" in url:
        # https://dev.azure.com/<org>[/<project>...]
        part = url.split("dev.azure.com/")[-1]
        return part.split("/")[0]
    if "visualstudio.com" in url:
        # https://<org>.visualstudio.com
        return url.split("//")[1].split(".")[0]
    # Already just the org name
    return url


def _make_ado_mcp(domains: list[str], tool_name_prefix: str) -> MCPTools:
    """
    Build an MCPTools instance connecting to the Azure DevOps MCP server.

    Parameters
    ----------
    domains:
        ADO domain names to load.  Always include "core".
        Example: ["core", "pipelines", "repositories"]
    tool_name_prefix:
        Short prefix added to every exposed tool name to avoid collisions
        when multiple MCPTools instances share the same agent.
    """
    ado_url = os.getenv("AZURE_DEVOPS_URL", "").rstrip("/")
    # Accept both names; AZURE_DEVOPS_EXT_PAT is what @azure-devops/mcp reads
    ado_pat = os.getenv("AZURE_DEVOPS_PAT", "") or os.getenv("AZURE_DEVOPS_EXT_PAT", "")

    if not ado_url:
        _log.warning(
            "AZURE_DEVOPS_URL is not set — Azure DevOps MCP tools will be unavailable. "
            "Set AZURE_DEVOPS_URL=https://dev.azure.com/yourorg in .env"
        )
        raise ValueError("AZURE_DEVOPS_URL not configured")

    if not ado_pat:
        _log.warning(
            "AZURE_DEVOPS_PAT is not set — Azure DevOps MCP will attempt browser-based "
            "interactive auth, which fails in headless / Docker environments. "
            "Set AZURE_DEVOPS_PAT in .env for non-interactive operation."
        )

    org = _extract_ado_org(ado_url)

    # @azure-devops/mcp v2.7+ requires --authentication pat and PERSONAL_ACCESS_TOKEN
    # as base64("{email}:{pat}").  The package's auth.js decodes the value, splits on
    # the first ':', and passes the right-hand side to getPersonalAccessTokenHandler.
    ado_email = os.getenv("AZURE_DEVOPS_EMAIL", "")
    b64_pat = base64.b64encode(f"{ado_email}:{ado_pat}".encode()).decode()

    env = {
        **os.environ,
        # Required by @azure-devops/mcp v2.7+ when --authentication pat is used
        "PERSONAL_ACCESS_TOKEN": b64_pat,
        # Keep legacy var for any older tooling that reads it
        "AZURE_DEVOPS_EXT_PAT": ado_pat,
    }

    # Build args: npx -y @azure-devops/mcp <org> --authentication pat [-d <domain> ...]
    args: list[str] = ["-y", "@azure-devops/mcp", org, "--authentication", "pat"]
    if domains:
        args += ["-d"] + domains

    server_params = StdioServerParameters(
        command="npx",
        args=args,
        env=env,
    )

    return MCPTools(
        server_params=server_params,
        transport="stdio",
        tool_name_prefix=tool_name_prefix,
        timeout_seconds=30,
    )


# ---------------------------------------------------------------------------
# Singleton — one shared ADO MCP process for stdio fallback (dev mode).
# All domains included in the superset so no tool filtering is lost on fallback.
# Returns [] when AZURE_DEVOPS_URL or AZURE_DEVOPS_PAT are not configured.
# ---------------------------------------------------------------------------
_ADO_MCP_SINGLETON: MCPTools | None = None


def _get_ado_mcp_singleton() -> list:
    """Return singleton list.

    Priority:
    1. HTTP — connect to the ado-mcp Docker service (ADO_MCP_URL).
    2. stdio fallback — spawn npx @azure-devops/mcp locally inside qap-api.
    Returns [] when neither AZURE_DEVOPS_URL nor AZURE_DEVOPS_EXT_PAT are set.
    """
    ado_url = os.getenv("AZURE_DEVOPS_URL", "").rstrip("/")
    ado_ext_pat = os.getenv("AZURE_DEVOPS_EXT_PAT", "")

    if not ado_url:
        _log.warning(
            "AZURE_DEVOPS_URL not set — ADO MCP tools unavailable. "
            "Set AZURE_DEVOPS_URL=https://dev.azure.com/yourorg in .env"
        )
        return []

    if not ado_ext_pat:
        _log.warning(
            "AZURE_DEVOPS_EXT_PAT not set — ADO MCP tools unavailable. "
            "Set AZURE_DEVOPS_EXT_PAT=<your-pat> in .env."
        )
        return []

    global _ADO_MCP_SINGLETON
    if _ADO_MCP_SINGLETON is not None:
        return [_ADO_MCP_SINGLETON]

    # ---------------------------------------------------------------------------
    # Mode 1 — SSE connection to the ado-mcp Docker service (preferred).
    # ---------------------------------------------------------------------------
    ado_mcp_url = os.getenv("ADO_MCP_URL", "").rstrip("/")
    if ado_mcp_url and _ado_mcp_service_reachable(ado_mcp_url):
        _ADO_MCP_SINGLETON = MCPTools(
            url=ado_mcp_url,
            transport="streamable-http",
            tool_name_prefix="ado_",
            timeout_seconds=60,
        )
        return [_ADO_MCP_SINGLETON]

    if ado_mcp_url:
        log_warning(
            "ADO_MCP_URL is set to %s but the service is not reachable. "
            "Falling back to npx stdio. Start the service with: docker compose up -d ado-mcp",
            ado_mcp_url,
        )

    # ---------------------------------------------------------------------------
    # Mode 2 — stdio fallback: spawn npx @azure-devops/mcp inside qap-api.
    # ---------------------------------------------------------------------------
    _ADO_MCP_SINGLETON = _make_ado_mcp(
        domains=["core", "pipelines", "repositories", "work-items"],
        tool_name_prefix="ado_",
    )
    return [_ADO_MCP_SINGLETON]


# ---------------------------------------------------------------------------
# Service availability cache
# Probes the ADO MCP HTTP service at most once per process startup.
# ---------------------------------------------------------------------------
_ADO_SERVICE_CHECKED: bool = False
_ADO_SERVICE_AVAILABLE: bool = False
_ADO_SERVICE_URL: str = ""


def _get_ado_service_availability() -> tuple[bool, str]:
    """Return (http_available, service_url), probing the TCP port at most once."""
    global _ADO_SERVICE_CHECKED, _ADO_SERVICE_AVAILABLE, _ADO_SERVICE_URL
    if not _ADO_SERVICE_CHECKED:
        mcp_url = os.getenv("ADO_MCP_URL", "").rstrip("/")
        _ADO_SERVICE_URL = mcp_url
        _ADO_SERVICE_AVAILABLE = bool(mcp_url and _ado_mcp_service_reachable(mcp_url))
        if mcp_url and not _ADO_SERVICE_AVAILABLE:
            log_warning(
                "ADO_MCP_URL is set to %s but the service is not reachable. "
                "Falling back to npx stdio. Start: docker compose up -d ado-mcp",
                mcp_url,
            )
        _ADO_SERVICE_CHECKED = True
    return _ADO_SERVICE_AVAILABLE, _ADO_SERVICE_URL


def _make_ado_mcp_http_filtered(include_tools: list[str]) -> MCPTools | None:
    """Create a per-agent filtered MCPTools for HTTP mode.

    Returns None when credentials are missing or the HTTP service is unavailable.
    ``include_tools`` uses raw ADO MCP tool names (without the ``ado_`` prefix).
    """
    ado_url = os.getenv("AZURE_DEVOPS_URL", "").rstrip("/")
    ado_ext_pat = os.getenv("AZURE_DEVOPS_EXT_PAT", "")
    if not ado_url or not ado_ext_pat:
        return None

    available, mcp_url = _get_ado_service_availability()
    if not available:
        return None

    return MCPTools(
        url=mcp_url,
        transport="streamable-http",
        tool_name_prefix="ado_",
        include_tools=include_tools,
        timeout_seconds=60,
    )


# ---------------------------------------------------------------------------
# Per-agent tool subsets
# Only the ADO MCP tools each agent actually needs (65 total → 6-12 per agent).
# Tool names are the raw names from the MCP server (without the ado_ prefix).
# ---------------------------------------------------------------------------

# Architect: reads ADO work items as requirements — no pipeline or repo access
_ARCHITECT_ADO_TOOLS = [
    "core_list_projects",              # discover available projects
    "wit_get_work_item",               # read a specific work item by ID
    "wit_get_work_items_batch_by_ids", # bulk-fetch linked work items
    "wit_my_work_items",               # list work items assigned to the current user
    "wit_list_backlogs",               # list sprint / backlog contents
    "wit_list_backlog_work_items",     # expand backlog to get individual items
    "wit_query_by_wiql",               # WIQL query for flexible work item search
    "wit_list_work_item_comments",     # read discussion / acceptance criteria notes
    "wit_get_work_item_type",          # resolve work item type metadata (story / bug)
]

# Pipeline Analyst: CI build logs and run status — no work item writes
_PIPELINE_ANALYST_ADO_TOOLS = [
    "core_list_projects",              # discover available projects
    "core_list_project_teams",         # resolve team context
    "pipelines_get_builds",            # list pipeline builds for a definition
    "pipelines_get_build_log",         # fetch the full build log
    "pipelines_get_build_log_by_id",   # fetch a specific log section by ID
    "pipelines_get_build_changes",     # commits associated with a build
    "pipelines_get_build_status",      # quick pass/fail status check
    "pipelines_list_runs",             # list pipeline runs (new Runs API)
    "pipelines_get_run",               # get details of a specific run
    "pipelines_list_artifacts",        # list build artifacts (Allure, JUnit, etc.)
    "pipelines_download_artifact",     # download an artifact for parsing
]

# CI Log Analyzer: reads logs + creates / updates work items for RCA tickets
_CI_LOG_ANALYZER_ADO_TOOLS = [
    "core_list_projects",              # discover available projects
    "pipelines_get_builds",            # list recent builds
    "pipelines_get_build_log",         # fetch full log
    "pipelines_get_build_log_by_id",   # fetch targeted log section
    "pipelines_get_build_status",      # quick status check
    "pipelines_list_runs",             # list runs (new API)
    "pipelines_get_run",               # inspect specific run
    "pipelines_list_artifacts",        # find test result artifacts
    "pipelines_download_artifact",     # download for parsing
    "wit_create_work_item",            # create RCA bug ticket after HITL approval
    "wit_update_work_item",            # update work item with findings
    "wit_get_work_item",               # check for existing tickets before creating
    "wit_add_work_item_comment",       # attach RCA findings as a comment
    "wit_query_by_wiql",               # search for duplicate open bugs
    "wit_get_work_item_type",          # resolve work item type before creation
]

# Impact Analyst: work item AC extraction + ADO repo PR analysis
_IMPACT_ANALYST_ADO_TOOLS = [
    "core_list_projects",                          # discover projects
    "wit_get_work_item",                           # read linked work items for ACs
    "wit_get_work_items_batch_by_ids",             # bulk fetch linked items
    "wit_list_backlog_work_items",                 # enumerate sprint items
    "wit_query_by_wiql",                           # flexible work item search
    "repo_get_pull_request_by_id",                 # read PR under analysis
    "repo_get_pull_request_changes",               # get changed files in the PR
    "repo_list_pull_requests_by_repo_or_project",  # find PRs for a repo
    "repo_list_directory",                         # browse repo structure
    "repo_get_file_content",                       # read source files
]


# ---------------------------------------------------------------------------
# Per-agent factory functions
# ---------------------------------------------------------------------------

def get_ado_mcp_for_pipeline_analyst() -> list:
    """
    ADO MCP tools for the Pipeline Analyst agent.

    Curated to 11 tools: build/run status, log fetching, artifact access.
    No work-item writes — Pipeline Analyst is read-only for CI correlation.
    """
    http = _make_ado_mcp_http_filtered(_PIPELINE_ANALYST_ADO_TOOLS)
    if http:
        return [http]
    return _get_ado_mcp_singleton()


def get_ado_mcp_for_ci_log_analyzer() -> list:
    """
    ADO MCP tools for the CI Log Analyzer agent.

    Curated to 15 tools: log reads + work-item create/update for RCA tickets.
    Work-item writes are only invoked after HITL approval in the UI.
    """
    http = _make_ado_mcp_http_filtered(_CI_LOG_ANALYZER_ADO_TOOLS)
    if http:
        return [http]
    return _get_ado_mcp_singleton()


def get_ado_mcp_for_architect() -> list:
    """
    ADO MCP tools for the Architect agent.

    Curated to 9 tools: work-item reads only — no pipeline or repo toolsets.
    Architect reads ADO User Stories / Bugs / Epics as requirements.
    """
    http = _make_ado_mcp_http_filtered(_ARCHITECT_ADO_TOOLS)
    if http:
        return [http]
    return _get_ado_mcp_singleton()


def get_ado_mcp_for_impact_analyst() -> list:
    """
    ADO MCP tools for the Impact Analyst agent.

    Curated to 10 tools: work-item AC extraction + ADO repo PR diff analysis.
    No pipeline toolset — CI correlation is handled by Pipeline Analyst.
    """
    http = _make_ado_mcp_http_filtered(_IMPACT_ANALYST_ADO_TOOLS)
    if http:
        return [http]
    return _get_ado_mcp_singleton()