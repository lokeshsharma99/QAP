"""
app/atlassian_mcp.py
====================

Factory functions returning Agno MCPTools instances wired to the official
Atlassian Rovo MCP Server (cloud-hosted, no local install required).

The Atlassian Rovo MCP Server runs at:
    https://mcp.atlassian.com/v1/mcp

It is accessed via the `mcp-remote` stdio proxy with API token authentication
(headless — no browser required).  The proxy pattern keeps transport consistent
with the GitHub and Azure DevOps MCP implementations (all stdio via npx).

Supported Atlassian products:
  Jira        — issues, sprints, boards, work items, acceptance criteria
  Confluence  — pages, spaces, search, create / update docs
  Compass     — components, dependencies, service catalog

Authentication setup
--------------------
1. Create an Atlassian API token at:
   https://id.atlassian.com/manage-profile/security/api-tokens
2. Ask your Atlassian org admin to enable API token auth:
   Atlassian Administration → Security → Rovo MCP Server settings
3. Set in .env:
     ATLASSIAN_URL=https://yourorg.atlassian.net
     ATLASSIAN_EMAIL=user@example.com
     ATLASSIAN_API_TOKEN=ATATT3x...
   Optional (reduces tool calls per session):
     ATLASSIAN_CLOUD_ID=      # found via https://yourorg.atlassian.net/_edge/tenant_info
     ATLASSIAN_JIRA_PROJECT=  # default Jira project key e.g. QAP
     ATLASSIAN_CONFLUENCE_SPACE=  # default Confluence spaceId

Usage by agent
--------------
  Architect       — Jira (read issues / ACs as requirements)
  Scribe          — Jira + Confluence (verify ACs, attach .feature links)
  CI Log Analyzer — Jira (create bugs from RCA after HITL approval)
"""

import base64
import logging
import os
import socket
import urllib.parse

from agno.tools.mcp import MCPTools
from mcp.client.stdio import StdioServerParameters

_log = logging.getLogger(__name__)

# Atlassian Rovo MCP remote endpoint
_ATLASSIAN_MCP_URL = "https://mcp.atlassian.com/v1/mcp"


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _make_atlassian_mcp(tool_name_prefix: str) -> MCPTools:
    """
    Build an MCPTools instance connecting to the Atlassian Rovo MCP Server
    via the mcp-remote stdio proxy with API token (Basic auth) authentication.

    Parameters
    ----------
    tool_name_prefix:
        Short prefix added to every exposed tool name to avoid collisions.
    """
    email = os.getenv("ATLASSIAN_EMAIL", "")
    api_token = os.getenv("ATLASSIAN_API_TOKEN", "")

    if not email or not api_token:
        _log.warning(
            "ATLASSIAN_EMAIL or ATLASSIAN_API_TOKEN not set — Atlassian MCP unavailable. "
            "Set both in .env and ensure your org admin has enabled API token auth in "
            "Atlassian Administration → Security → Rovo MCP Server settings."
        )
        raise ValueError("Atlassian credentials not configured")

    # mcp-remote expects the Authorization header value as: Basic <base64(email:token)>
    b64_creds = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    auth_header = f"Authorization:Basic {b64_creds}"

    server_params = StdioServerParameters(
        command="npx",
        args=[
            "-y",
            "mcp-remote",
            _ATLASSIAN_MCP_URL,
            "--header",
            auth_header,
            # Suppress interactive prompts; fail fast in headless mode
            "--allow-http",
        ],
        env={**os.environ},
    )

    return MCPTools(
        server_params=server_params,
        transport="stdio",
        tool_name_prefix=tool_name_prefix,
        timeout_seconds=30,
    )


# ---------------------------------------------------------------------------
# Per-agent factory functions
# Each returns a list so agents can unpack: tools=[..., *get_atlassian_mcp_for_X()]
# Returns [] when ATLASSIAN_EMAIL / ATLASSIAN_API_TOKEN are not configured.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Singleton — one shared Atlassian MCP process for all agents.
# Using a single instance avoids spawning multiple npx/mcp-remote processes
# at startup (which caused simultaneous connection timeouts).
# ---------------------------------------------------------------------------
_ATLASSIAN_MCP_SINGLETON: MCPTools | None = None


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


def _get_atlassian_mcp_singleton() -> MCPTools:
    """Return the module-level singleton.

    Priority:
    1. HTTP — connect to the atlassian-mcp Docker service (ATLASSIAN_MCP_URL).
       The service wraps mcp-remote stdio via supergateway streamable-HTTP.
    2. stdio fallback — spawn npx mcp-remote locally inside qap-api.
       Used when the atlassian-mcp container is not running.
    Raises ValueError when credentials are not configured.
    """
    email = os.getenv("ATLASSIAN_EMAIL", "")
    api_token = os.getenv("ATLASSIAN_API_TOKEN", "")

    if not email or not api_token:
        _log.warning(
            "ATLASSIAN_EMAIL or ATLASSIAN_API_TOKEN not set — Atlassian MCP unavailable. "
            "Set both in .env and ensure your org admin has enabled API token auth in "
            "Atlassian Administration → Security → Rovo MCP Server settings."
        )
        raise ValueError("Atlassian credentials not configured")

    global _ATLASSIAN_MCP_SINGLETON
    if _ATLASSIAN_MCP_SINGLETON is not None:
        return _ATLASSIAN_MCP_SINGLETON

    # -------------------------------------------------------------------------
    # Mode 1 — streamable-HTTP connection to the atlassian-mcp Docker service.
    # -------------------------------------------------------------------------
    atlassian_mcp_url = os.getenv("ATLASSIAN_MCP_URL", "").rstrip("/")
    if atlassian_mcp_url and _atlassian_mcp_service_reachable(atlassian_mcp_url):
        _ATLASSIAN_MCP_SINGLETON = MCPTools(
            url=atlassian_mcp_url,
            transport="streamable-http",
            tool_name_prefix="atl_",
            timeout_seconds=60,
        )
        return _ATLASSIAN_MCP_SINGLETON

    if atlassian_mcp_url:
        _log.warning(
            "ATLASSIAN_MCP_URL is set to %s but the service is not reachable. "
            "Falling back to npx stdio. Start with: docker compose up -d atlassian-mcp",
            atlassian_mcp_url,
        )

    # -------------------------------------------------------------------------
    # Mode 2 — stdio fallback: spawn npx mcp-remote inside qap-api.
    # -------------------------------------------------------------------------
    _ATLASSIAN_MCP_SINGLETON = _make_atlassian_mcp(tool_name_prefix="atl_")
    return _ATLASSIAN_MCP_SINGLETON


def get_atlassian_mcp_for_architect() -> list:
    """
    Atlassian MCP tools for the Architect agent.

    Architect uses these to:
    - Fetch Jira issues (User Stories, Epics, Bugs) as requirement sources
    - Read acceptance criteria from Jira descriptions and sub-tasks
    - Query Confluence knowledge bases for domain / business context
    - Understand sprint / backlog priority before producing an Execution Plan
    """
    try:
        return [_get_atlassian_mcp_singleton()]
    except Exception:
        return []


def get_atlassian_mcp_for_scribe() -> list:
    """
    Atlassian MCP tools for the Scribe agent.

    Scribe uses these to:
    - Cross-check all Jira ACs are covered in the generated Gherkin spec
    - Read Confluence test strategy / regression docs for reusable step patterns
    - Comment on Jira issues linking to generated .feature files
    """
    try:
        return [_get_atlassian_mcp_singleton()]
    except Exception:
        return []


def get_atlassian_mcp_for_ci_log_analyzer() -> list:
    """
    Atlassian MCP tools for the CI Log Analyzer agent.

    CI Log Analyzer uses these to:
    - Search for duplicate open Jira bugs before creating new ones
    - Create Jira bug tickets from RCA findings (after HITL approval)
    - Attach RCA report text to Jira issue descriptions and comments
    """
    try:
        return [_get_atlassian_mcp_singleton()]
    except Exception:
        return []
