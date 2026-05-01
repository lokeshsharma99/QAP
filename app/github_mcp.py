"""
app/github_mcp.py
=================

Factory functions that return pre-configured Agno MCPTools instances wired
to the official GitHub MCP server (@modelcontextprotocol/server-github).

The GitHub MCP server is invoked via `npx` (stdio transport) — no separate
container needed.  It reads GITHUB_TOKEN from the environment.

GitHub MCP Toolsets (controlled via GITHUB_TOOLSETS env var):
  repos         — repo contents, file reads, branch listing, code search
  issues        — create/read/list issues
  pull_requests — create/read/list PRs, reviews
  actions       — workflow runs, job logs, pipeline status
  discussions   — repo discussions
  search        — cross-repo code/user/repo search
  contexts      — meta: current repo/user context

AUT (GDS-Demo-App) Resources:
  Repo:         https://github.com/lokeshsharma99/GDS-Demo-App
  Production:   https://lokeshsharma99.github.io/GDS-Demo-App/
  Allure:       https://lokeshsharma99.github.io/GDS-Demo-App/allure-report/
  GitHub Project: https://github.com/users/lokeshsharma99/projects/6/views/1
  Wiki:         https://github.com/lokeshsharma99/GDS-Demo-App/wiki/
  SonarCloud:   https://sonarcloud.io/summary/overall?id=lokeshsharma99_GDS-Demo-App
  Pipeline:     GitHub Actions on GDS-Demo-App repo

Usage by agent
--------------
  Architect  — repos, issues, wiki (domain knowledge for requirement parsing)
  Discovery  — repos, wiki (wireframes + domain knowledge for AUT context)
  Engineer   — repos, pull_requests (create PRs, read existing code structure)
  Detective  — actions, repos (workflow runs, CI logs, test result artifacts)
"""

import os
from functools import lru_cache

import socket
import urllib.parse

from agno.utils.log import log_warning
from agno.tools.mcp import MCPTools
from mcp.client.stdio import StdioServerParameters

# ---------------------------------------------------------------------------
# AUT Constants — GDS Demo App
# ---------------------------------------------------------------------------
AUT_GITHUB_OWNER = os.getenv("AUT_GITHUB_OWNER", "lokeshsharma99")
AUT_GITHUB_REPO = os.getenv("AUT_GITHUB_REPO", "GDS-Demo-App")
AUT_GITHUB_REF = os.getenv("AUT_GITHUB_REPO_DEFAULT_BRANCH", "main")
AUT_GITHUB_REPO_FULL = f"{AUT_GITHUB_OWNER}/{AUT_GITHUB_REPO}"


def _github_mcp_service_reachable(url: str) -> bool:
    """Return True if the github-mcp Docker service TCP port is open."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or "github-mcp"
    port = parsed.port or 8080
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def _make_github_mcp(toolsets: list[str], tool_name_prefix: str) -> MCPTools:
    """
    Build an MCPTools instance connecting to the GitHub MCP server.

    Preferred: streamable-HTTP connection to the github-mcp Docker service
    (GITHUB_MCP_URL=http://github-mcp:8080).  Falls back to spawning the
    legacy npx stdio server when the Docker service is not reachable.

    Parameters
    ----------
    toolsets:
        List of GitHub MCP toolset names to enable.
        Options: repos, issues, pull_requests, actions, discussions, git, users
    tool_name_prefix:
        Short prefix added to every tool name to avoid collisions.
    """
    mcp_url = os.getenv("GITHUB_MCP_URL", "").rstrip("/")

    # ---------------------------------------------------------------------------
    # Mode 1 — HTTP connection to the github-mcp Docker service (preferred)
    # ghcr.io/github/github-mcp-server runs in HTTP mode on port 8080.
    # Requires Authorization: Bearer header with the GitHub token.
    # ---------------------------------------------------------------------------
    if mcp_url and _github_mcp_service_reachable(mcp_url):
        github_token = os.getenv("GITHUB_TOKEN", "")
        from agno.tools.mcp.params import StreamableHTTPClientParams
        return MCPTools(
            server_params=StreamableHTTPClientParams(
                url=mcp_url,
                headers={"Authorization": f"Bearer {github_token}"},
            ),
            transport="streamable-http",
            tool_name_prefix=tool_name_prefix,
            timeout_seconds=30,
        )

    if mcp_url:
        log_warning(
            "GITHUB_MCP_URL is set to %s but the service is not reachable. "
            "Falling back to npx stdio. Start the service with: docker compose up -d github-mcp",
            mcp_url,
        )

    # ---------------------------------------------------------------------------
    # Mode 2 — stdio fallback: spawn @modelcontextprotocol/server-github via npx.
    # Used in local dev when the github-mcp container is not running.
    # ---------------------------------------------------------------------------
    github_token = os.getenv("GITHUB_TOKEN", "")
    env = {
        **os.environ,
        "GITHUB_PERSONAL_ACCESS_TOKEN": github_token,
        "GITHUB_TOOLSETS": ",".join(toolsets),
    }
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env=env,
    )
    return MCPTools(
        server_params=server_params,
        transport="stdio",
        tool_name_prefix=tool_name_prefix,
        timeout_seconds=30,
    )


# ---------------------------------------------------------------------------
# Singleton — one shared GitHub MCP process for stdio fallback (dev mode).
# Used when the github-mcp Docker service is not running.  All toolsets are
# included in the superset so no tool filtering is lost in the fallback path.
# ---------------------------------------------------------------------------
_GITHUB_MCP_SINGLETON: MCPTools | None = None


def _get_github_mcp_singleton() -> MCPTools:
    """Return the module-level stdio singleton, creating it on first call."""
    global _GITHUB_MCP_SINGLETON
    if _GITHUB_MCP_SINGLETON is None:
        _GITHUB_MCP_SINGLETON = _make_github_mcp(
            toolsets=["repos", "issues", "pull_requests", "actions", "contexts"],
            tool_name_prefix="gh_",
        )
    return _GITHUB_MCP_SINGLETON


# ---------------------------------------------------------------------------
# Service availability cache
# Checked once on first factory call; subsequent calls skip the TCP probe.
# ---------------------------------------------------------------------------
_GITHUB_SERVICE_CHECKED: bool = False
_GITHUB_SERVICE_AVAILABLE: bool = False
_GITHUB_SERVICE_URL: str = ""


def _get_github_service_availability() -> tuple[bool, str]:
    """Return (http_available, service_url), probing the TCP port at most once."""
    global _GITHUB_SERVICE_CHECKED, _GITHUB_SERVICE_AVAILABLE, _GITHUB_SERVICE_URL
    if not _GITHUB_SERVICE_CHECKED:
        mcp_url = os.getenv("GITHUB_MCP_URL", "").rstrip("/")
        _GITHUB_SERVICE_URL = mcp_url
        _GITHUB_SERVICE_AVAILABLE = bool(mcp_url and _github_mcp_service_reachable(mcp_url))
        if mcp_url and not _GITHUB_SERVICE_AVAILABLE:
            log_warning(
                "GITHUB_MCP_URL is set to %s but the service is not reachable. "
                "Falling back to npx stdio. Start: docker compose up -d github-mcp",
                mcp_url,
            )
        _GITHUB_SERVICE_CHECKED = True
    return _GITHUB_SERVICE_AVAILABLE, _GITHUB_SERVICE_URL


def _make_github_mcp_http_filtered(include_tools: list[str]) -> MCPTools | None:
    """Create a per-agent filtered MCPTools for HTTP mode.

    Each agent gets only the tools it actually needs.  This prevents tool
    explosion: injecting 40+ tools from a single MCP server into every agent
    degrades LLM tool-selection accuracy and increases latency.

    Returns None when the HTTP service is unavailable — the caller falls back
    to the stdio singleton which exposes the full unfiltered tool list.

    ``include_tools`` uses raw MCP tool names (without the ``gh_`` prefix).
    """
    available, mcp_url = _get_github_service_availability()
    if not available:
        return None
    github_token = os.getenv("GITHUB_TOKEN", "")
    from agno.tools.mcp.params import StreamableHTTPClientParams
    return MCPTools(
        server_params=StreamableHTTPClientParams(
            url=mcp_url,
            headers={"Authorization": f"Bearer {github_token}"},
        ),
        transport="streamable-http",
        tool_name_prefix="gh_",
        include_tools=include_tools,
        timeout_seconds=30,
    )


# ---------------------------------------------------------------------------
# Per-agent tool subsets
# Only the GitHub tools each agent actually needs.  Keeping these small means
# the LLM context only contains relevant tools and avoids decision paralysis.
#
# Tool names are the raw names from the MCP server (without the gh_ prefix).
# ---------------------------------------------------------------------------

# Architect: reads requirements from Issues and wiki/docs — no write access
_ARCHITECT_GITHUB_TOOLS = [
    "get_file_contents",   # wiki, CHANGELOG, ADRs, domain knowledge docs
    "list_issues",         # enumerate GitHub Issues as requirements
    "issue_read",          # read single issue detail with acceptance criteria
    "search_issues",       # find related or duplicate issues
    "get_me",              # resolve current authenticated identity (context)
]

# Discovery: only needs file reads for wiki/wireframes before crawling
_DISCOVERY_GITHUB_TOOLS = [
    "get_file_contents",   # wiki pages, wireframes, existing Site Manifesto
]

# Engineer: full file-write + PR workflow for Look-Before-You-Leap pattern
_ENGINEER_GITHUB_TOOLS = [
    "get_file_contents",         # read existing POMs / step defs before writing
    "search_code",               # find existing patterns across the repo
    "list_branches",             # check open branches before creating a new one
    "create_branch",             # create feature branch for new automation
    "push_files",                # push generated POM + step def files
    "create_or_update_file",     # write individual files (fine-grained updates)
    "create_pull_request",       # open PR after code generation passes lint
    "list_pull_requests",        # avoid creating duplicate PRs
    "pull_request_read",         # read PR details to understand existing work
    "update_pull_request",       # update PR title / description / labels
    "list_commits",              # check recent commits before writing
]

# Detective: read-only CI + code correlation — no write access
_DETECTIVE_GITHUB_TOOLS = [
    "get_file_contents",   # read test files, CI YAML, Page Objects
    "list_commits",        # correlate failure timestamp with code commits
    "get_commit",          # inspect the exact files changed in a commit
    "search_code",         # find the affected test / POM file by pattern
    "list_issues",         # check whether failure matches a known open bug
    "issue_read",          # read issue detail + linked PRs
    "list_pull_requests",  # identify the PR that introduced the regression
    "pull_request_read",   # read PR diff to understand the breaking change
]

# Impact Analyst: PR analysis + issue AC extraction — read-only
_IMPACT_ANALYST_GITHUB_TOOLS = [
    "get_file_contents",   # read changed source files and AUT code
    "list_commits",        # enumerate commits in the change surface
    "get_commit",          # inspect file-level changes in each commit
    "list_pull_requests",  # list PRs to find the one under analysis
    "pull_request_read",   # read PR details, diff, changed files
    "search_code",         # find test coverage for changed components
    "list_issues",         # read linked issues for acceptance criteria
    "issue_read",          # read single issue detail + ACs
]

# Pipeline Analyst: CI pipeline correlation — read-only, no write
_PIPELINE_ANALYST_GITHUB_TOOLS = [
    "list_commits",        # correlate pipeline failure with recent commits
    "get_commit",          # read file-level changes in a specific commit
    "list_pull_requests",  # identify the triggering PR
    "pull_request_read",   # read PR description and diff
    "search_code",         # find related test patterns for context
    "list_issues",         # check for related known issues / bugs
]


# ---------------------------------------------------------------------------
# Per-agent factory functions
# Each function returns a list so agents can do: tools=[..., *get_github_mcp_for_X()]
# HTTP mode: returns a new MCPTools with only the agent's curated tool subset.
# stdio fallback: returns the shared singleton with all tools (dev mode only).
# ---------------------------------------------------------------------------

def get_github_mcp_for_architect() -> list:
    """
    GitHub MCP tools for the Architect agent.

    Curated to 5 tools: read Issues for requirements, read wiki/docs for domain
    context.  No write access, no PR or Actions toolsets.
    """
    http = _make_github_mcp_http_filtered(_ARCHITECT_GITHUB_TOOLS)
    if http:
        return [http]
    try:
        return [_get_github_mcp_singleton()]
    except Exception:
        return []


def get_github_mcp_for_discovery() -> list:
    """
    GitHub MCP tools for the Discovery agent.

    Curated to 1 tool: read wiki/wireframe pages for AUT context before crawling.
    """
    http = _make_github_mcp_http_filtered(_DISCOVERY_GITHUB_TOOLS)
    if http:
        return [http]
    try:
        return [_get_github_mcp_singleton()]
    except Exception:
        return []


def get_github_mcp_for_engineer() -> list:
    """
    GitHub MCP tools for the Engineer agent.

    Curated to 11 tools: full Look-Before-You-Leap read + write + PR workflow.
    No Issues, Actions, or Discussion toolsets.
    """
    http = _make_github_mcp_http_filtered(_ENGINEER_GITHUB_TOOLS)
    if http:
        return [http]
    try:
        return [_get_github_mcp_singleton()]
    except Exception:
        return []


def get_github_mcp_for_detective() -> list:
    """
    GitHub MCP tools for the Detective agent.

    Curated to 8 tools: read-only CI correlation and code inspection.
    No write access, no Actions toolset (CI logs come via ADO or custom tools).
    """
    http = _make_github_mcp_http_filtered(_DETECTIVE_GITHUB_TOOLS)
    if http:
        return [http]
    try:
        return [_get_github_mcp_singleton()]
    except Exception:
        return []


def get_github_mcp_for_impact_analyst() -> list:
    """
    GitHub MCP tools for the Impact Analyst agent.

    Curated to 8 tools: PR analysis, commit inspection, issue AC extraction.
    Read-only — no branch creation or file writes.
    """
    http = _make_github_mcp_http_filtered(_IMPACT_ANALYST_GITHUB_TOOLS)
    if http:
        return [http]
    try:
        return [_get_github_mcp_singleton()]
    except Exception:
        return []


def get_github_mcp_for_pipeline_analyst() -> list:
    """
    GitHub MCP tools for the Pipeline Analyst agent.

    Curated to 6 tools: commit/PR correlation for CI failure analysis.
    Read-only — CI log access handled via the ADO MCP tools.
    """
    http = _make_github_mcp_http_filtered(_PIPELINE_ANALYST_GITHUB_TOOLS)
    if http:
        return [http]
    try:
        return [_get_github_mcp_singleton()]
    except Exception:
        return []
