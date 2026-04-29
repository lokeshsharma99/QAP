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
    )


# ---------------------------------------------------------------------------
# Per-agent factory functions
# Each returns a list so agents can unpack: tools=[..., *get_atlassian_mcp_for_X()]
# Returns [] when ATLASSIAN_EMAIL / ATLASSIAN_API_TOKEN are not configured.
# ---------------------------------------------------------------------------

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
        return [_make_atlassian_mcp(tool_name_prefix="atl_arch_")]
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
        return [_make_atlassian_mcp(tool_name_prefix="atl_sc_")]
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
        return [_make_atlassian_mcp(tool_name_prefix="atl_ci_")]
    except Exception:
        return []
