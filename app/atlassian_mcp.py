"""
app/atlassian_mcp.py
====================

Factory functions returning Agno MCPTools instances wired to the
sooperset/mcp-atlassian server (https://github.com/sooperset/mcp-atlassian).

This replaces the official Atlassian Rovo MCP which exposed only 2 tools and
required org-admin permission to enable API token auth.  The sooperset server
exposes 72 Jira + Confluence tools and works out-of-the-box with a standard
API token.

REPLACED: https://mcp.atlassian.com/v1/mcp (Rovo MCP — org-admin required)

Transport (priority order)
--------------------------
1. HTTP  — connect to the atlassian-mcp Docker service at ATLASSIAN_MCP_URL
           (http://atlassian-mcp:8933/mcp).  No subprocess overhead.
2. stdio — spawn ``uvx mcp-atlassian`` locally (fallback for local dev outside
           Docker).  Requires ``uvx`` / ``uv`` installed in PATH.

Authentication
--------------
Credentials are read from the same env vars already set in your .env:
  ATLASSIAN_URL        → JIRA_URL for the server
  ATLASSIAN_EMAIL      → JIRA_USERNAME + CONFLUENCE_USERNAME
  ATLASSIAN_API_TOKEN  → JIRA_API_TOKEN + CONFLUENCE_API_TOKEN
  ATLASSIAN_CONFLUENCE_URL (optional) → CONFLUENCE_URL (defaults to ATLASSIAN_URL/wiki)

Supported products
------------------
  Jira        — jira_get_issue, jira_search, jira_create_issue, jira_add_comment, ...
  Confluence  — confluence_search, confluence_get_page, confluence_create_page, ...
  (72 tools total — see https://mcp-atlassian.soomiles.com/docs/tools-reference)
"""

import logging
import os
import socket
import urllib.parse

from agno.tools.mcp import MCPTools
from mcp.client.stdio import StdioServerParameters

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Service availability cache
# Probes the atlassian-mcp HTTP service at most once per process startup.
# ---------------------------------------------------------------------------
_ATLASSIAN_SERVICE_CHECKED: bool = False
_ATLASSIAN_SERVICE_AVAILABLE: bool = False
_ATLASSIAN_SERVICE_URL: str = ""


def _atlassian_mcp_service_reachable(url: str) -> bool:
    """Return True if the atlassian-mcp Docker service TCP port is open."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or "atlassian-mcp"
    port = parsed.port or 8933
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def _get_atlassian_service_availability() -> tuple[bool, str]:
    """Return (http_available, service_url), probing the TCP port at most once."""
    global _ATLASSIAN_SERVICE_CHECKED, _ATLASSIAN_SERVICE_AVAILABLE, _ATLASSIAN_SERVICE_URL
    if not _ATLASSIAN_SERVICE_CHECKED:
        mcp_url = os.getenv("ATLASSIAN_MCP_URL", "").rstrip("/")
        _ATLASSIAN_SERVICE_URL = mcp_url
        _ATLASSIAN_SERVICE_AVAILABLE = bool(mcp_url and _atlassian_mcp_service_reachable(mcp_url))
        if mcp_url and not _ATLASSIAN_SERVICE_AVAILABLE:
            _log.warning(
                "ATLASSIAN_MCP_URL is set to %s but the service is not reachable. "
                "Falling back to uvx stdio. Start: docker compose up -d atlassian-mcp",
                mcp_url,
            )
        _ATLASSIAN_SERVICE_CHECKED = True
    return _ATLASSIAN_SERVICE_AVAILABLE, _ATLASSIAN_SERVICE_URL


# ---------------------------------------------------------------------------
# Internal helper — HTTP mode (per-agent filtered)
# ---------------------------------------------------------------------------

def _make_atlassian_mcp_http_filtered(include_tools: list[str]) -> MCPTools | None:
    """Create a per-agent filtered MCPTools for the atlassian-mcp HTTP service.

    ``include_tools`` uses raw server tool names (e.g. ``["jira_get_issue"]``).
    Tools are exposed without an additional prefix since ``jira_`` and
    ``confluence_`` prefixes already make them self-documenting.

    Returns None when the HTTP service is unreachable.
    """
    available, mcp_url = _get_atlassian_service_availability()
    if not available:
        return None

    return MCPTools(
        url=mcp_url,
        transport="streamable-http",
        include_tools=include_tools,
        timeout_seconds=60,
    )


# ---------------------------------------------------------------------------
# Internal helper — stdio fallback (local dev outside Docker)
# ---------------------------------------------------------------------------

def _make_atlassian_mcp_stdio() -> MCPTools:
    """Spawn mcp-atlassian via ``uvx`` as a stdio subprocess (local dev fallback).

    Raises ValueError when ATLASSIAN_EMAIL / ATLASSIAN_API_TOKEN are not set.
    """
    jira_url = os.getenv("ATLASSIAN_URL") or os.getenv("JIRA_URL", "")
    email = os.getenv("ATLASSIAN_EMAIL") or os.getenv("JIRA_USERNAME", "")
    api_token = os.getenv("ATLASSIAN_API_TOKEN") or os.getenv("JIRA_API_TOKEN", "")
    confluence_url = (
        os.getenv("ATLASSIAN_CONFLUENCE_URL")
        or os.getenv("CONFLUENCE_URL")
        or (f"{jira_url}/wiki" if jira_url else "")
    )

    if not email or not api_token:
        raise ValueError(
            "ATLASSIAN_EMAIL and ATLASSIAN_API_TOKEN must be set for Atlassian MCP. "
            "See example.env for setup instructions."
        )

    subprocess_env = {
        **os.environ,
        "JIRA_URL": jira_url,
        "JIRA_USERNAME": email,
        "JIRA_API_TOKEN": api_token,
        "CONFLUENCE_URL": confluence_url,
        "CONFLUENCE_USERNAME": email,
        "CONFLUENCE_API_TOKEN": api_token,
    }

    server_params = StdioServerParameters(
        command="uvx",
        args=["mcp-atlassian", "--transport", "stdio"],
        env=subprocess_env,
    )

    return MCPTools(
        server_params=server_params,
        transport="stdio",
        timeout_seconds=60,
    )


# ---------------------------------------------------------------------------
# Singleton for stdio mode (avoid spawning multiple subprocesses)
# ---------------------------------------------------------------------------
_ATLASSIAN_MCP_STDIO_SINGLETON: MCPTools | None = None


def _get_atlassian_mcp_singleton() -> MCPTools:
    """Return shared stdio singleton (fallback for local dev outside Docker)."""
    global _ATLASSIAN_MCP_STDIO_SINGLETON
    if _ATLASSIAN_MCP_STDIO_SINGLETON is None:
        _ATLASSIAN_MCP_STDIO_SINGLETON = _make_atlassian_mcp_stdio()
    return _ATLASSIAN_MCP_STDIO_SINGLETON


# ---------------------------------------------------------------------------
# Per-agent tool subsets
#
# Tool names match the mcp-atlassian server's native names.
# See: https://mcp-atlassian.soomiles.com/docs/tools-reference
#
# Read-only:  jira_get_issue, jira_search, confluence_search, confluence_get_page
# Write:      jira_create_issue, jira_update_issue, jira_add_comment,
#             jira_transition_issue
# ---------------------------------------------------------------------------

# Architect: parse Jira requirements + Confluence domain context (read-only)
_ARCHITECT_ATLASSIAN_TOOLS = [
    "jira_get_issue",        # fetch full issue (summary, description, ACs, priority)
    "jira_search",           # JQL search for related issues in the project
    "confluence_search",     # find domain knowledge and architecture docs
    "confluence_get_page",   # read specific test-strategy or spec page
]

# Scribe: cross-check ACs; find reusable Gherkin steps in Confluence (read-only)
_SCRIBE_ATLASSIAN_TOOLS = [
    "jira_get_issue",        # verify ACs after Architect handoff
    "confluence_search",     # find step libraries and test-strategy docs
    "confluence_get_page",   # read the test-strategy doc content
]

# CI Log Analyzer: duplicate detection + ticket creation / commenting after HITL
_CI_LOG_ANALYZER_ATLASSIAN_TOOLS = [
    "jira_search",           # find duplicate open bugs by summary / project
    "jira_get_issue",        # inspect existing issue before creating a duplicate
    "jira_create_issue",     # create new bug ticket (after HITL approval)
    "jira_add_comment",      # add RCA comment to existing ticket
    "jira_transition_issue", # move ticket to In Progress / In Review
]

# Impact Analyst: trace PR changes back to Jira ACs (read-only)
_IMPACT_ANALYST_ATLASSIAN_TOOLS = [
    "jira_get_issue",        # get ACs from the issue linked to the PR
    "jira_search",           # find other related issues in the project
    "confluence_search",     # find domain / test-coverage docs
]

# Pipeline Analyst: link CI failures to Jira issues to understand intent (read-only)
_PIPELINE_ANALYST_ATLASSIAN_TOOLS = [
    "jira_search",           # look up issues by project / component
    "jira_get_issue",        # get full issue detail (intended behaviour)
]


# ---------------------------------------------------------------------------
# Per-agent factory functions
# Each returns a list so agents can unpack: tools=[..., *get_atlassian_mcp_for_X()]
# HTTP mode:   returns a new per-agent filtered MCPTools.
# stdio mode:  returns the shared singleton (all tools exposed).
# Returns []   when credentials are not configured or service is unavailable.
# ---------------------------------------------------------------------------

def get_atlassian_mcp_for_architect() -> list:
    """Atlassian MCP tools for the Architect agent (Jira + Confluence read)."""
    http = _make_atlassian_mcp_http_filtered(_ARCHITECT_ATLASSIAN_TOOLS)
    if http:
        return [http]
    try:
        return [_get_atlassian_mcp_singleton()]
    except Exception:
        return []


def get_atlassian_mcp_for_scribe() -> list:
    """Atlassian MCP tools for the Scribe agent (AC cross-check + Confluence)."""
    http = _make_atlassian_mcp_http_filtered(_SCRIBE_ATLASSIAN_TOOLS)
    if http:
        return [http]
    try:
        return [_get_atlassian_mcp_singleton()]
    except Exception:
        return []


def get_atlassian_mcp_for_ci_log_analyzer() -> list:
    """Atlassian MCP tools for the CI Log Analyzer (dup check + ticket creation)."""
    http = _make_atlassian_mcp_http_filtered(_CI_LOG_ANALYZER_ATLASSIAN_TOOLS)
    if http:
        return [http]
    try:
        return [_get_atlassian_mcp_singleton()]
    except Exception:
        return []


def get_atlassian_mcp_for_impact_analyst() -> list:
    """Atlassian MCP tools for the Impact Analyst (Jira AC tracing)."""
    http = _make_atlassian_mcp_http_filtered(_IMPACT_ANALYST_ATLASSIAN_TOOLS)
    if http:
        return [http]
    try:
        return [_get_atlassian_mcp_singleton()]
    except Exception:
        return []


def get_atlassian_mcp_for_pipeline_analyst() -> list:
    """Atlassian MCP tools for the Pipeline Analyst (CI failure → Jira linking)."""
    http = _make_atlassian_mcp_http_filtered(_PIPELINE_ANALYST_ATLASSIAN_TOOLS)
    if http:
        return [http]
    try:
        return [_get_atlassian_mcp_singleton()]
    except Exception:
        return []

