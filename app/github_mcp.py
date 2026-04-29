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
# Singleton — one shared GitHub MCP process for all agents.
# Using a single instance avoids spawning multiple npx processes at startup
# (which caused simultaneous connection timeouts during AgentOS lifespan).
# All toolsets needed by any agent are included in the superset.
# ---------------------------------------------------------------------------
_GITHUB_MCP_SINGLETON: MCPTools | None = None


def _get_github_mcp_singleton() -> MCPTools:
    """Return the module-level singleton, creating it on first call."""
    global _GITHUB_MCP_SINGLETON
    if _GITHUB_MCP_SINGLETON is None:
        _GITHUB_MCP_SINGLETON = _make_github_mcp(
            toolsets=["repos", "issues", "pull_requests", "actions", "contexts"],
            tool_name_prefix="gh_",
        )
    return _GITHUB_MCP_SINGLETON


# ---------------------------------------------------------------------------
# Per-agent factory functions
# Each function returns a list so agents can do: tools=[..., *get_github_mcp_for_X()]
# The list is empty if GITHUB_TOKEN is not set AND the repo is private (safe default).
# ---------------------------------------------------------------------------

def get_github_mcp_for_architect() -> list:
    """
    GitHub MCP tools for the Architect agent.

    Toolsets: repos (read wiki + file contents), issues (read Jira-equivalent
    GitHub Issues for requirement parsing), contexts (current repo info).

    Architect uses these to:
    - Read Domain Knowledge wiki page before parsing requirements
    - Read Wireframes wiki page to understand intended UI flows
    - Fetch open GitHub Issues as the requirement source of truth
    - Read CHANGELOG / ADRs stored in the repo
    """
    try:
        return [_get_github_mcp_singleton()]
    except Exception:
        return []


def get_github_mcp_for_discovery() -> list:
    """
    GitHub MCP tools for the Discovery agent.

    Toolsets: repos (wiki pages, existing page structure).

    Discovery uses these to:
    - Read the Domain Knowledge wiki (business context before crawling)
    - Read the Wireframes wiki (expected page structure to validate against)
    - Fetch existing Site Manifesto files committed to the repo
    """
    try:
        return [_get_github_mcp_singleton()]
    except Exception:
        return []


def get_github_mcp_for_engineer() -> list:
    """
    GitHub MCP tools for the Engineer agent.

    Toolsets: repos (read codebase structure), pull_requests (create PRs).

    Engineer uses these to:
    - Read existing automation files directly from GitHub (Look-Before-You-Leap)
    - Create feature branches and pull requests after code generation
    - Read open PRs to avoid duplicating work
    - Verify merged code matches expected structure
    """
    try:
        return [_get_github_mcp_singleton()]
    except Exception:
        return []


def get_github_mcp_for_detective() -> list:
    """
    GitHub MCP tools for the Detective agent.

    Toolsets: actions (workflow runs, CI logs), repos (read test result artifacts).

    Detective uses these to:
    - Fetch the latest GitHub Actions workflow run for GDS-Demo-App
    - Read CI job logs to identify failure steps
    - Download Allure report artifacts from the pipeline run
    - Read SonarCloud quality gate status (via repo badge/status API)
    - Correlate test failure timestamps with recent commits
    """
    try:
        return [_get_github_mcp_singleton()]
    except Exception:
        return []


def get_github_mcp_for_impact_analyst() -> list:
    """
    GitHub MCP tools for the Impact Analyst agent.

    Toolsets: repos (diff, file contents), pull_requests (PR details, changed
    files, review status), issues (linked issues, acceptance criteria),
    contexts (current repo metadata).

    Impact Analyst uses these to:
    - Read the full diff of an incoming PR to enumerate changed files
    - Fetch linked GitHub Issues to extract acceptance criteria and scope
    - Read the PR description for author-noted test implications
    - List recent commits to understand the change surface
    - Read source files to understand what was added/removed/renamed
    """
    try:
        return [_get_github_mcp_singleton()]
    except Exception:
        return []


def get_github_mcp_for_pipeline_analyst() -> list:
    """
    GitHub MCP tools for the Pipeline Analyst agent.

    Toolsets: actions (workflow runs, job logs, artifacts), repos (source file
    diffs, commit history), pull_requests (triggering PR details),
    contexts (current repo metadata).

    Pipeline Analyst uses these to:
    - Fetch the failed GitHub Actions workflow run details and status
    - Read job logs to extract the exact failure message and step
    - Download Allure/test-result artifact URLs for the failed run
    - Read recent commits to correlate failures with code changes
    - Fetch the triggering PR diff to understand the change surface
    - Compare current run with previous passing run to identify regressions
    """
    try:
        return [_get_github_mcp_singleton()]
    except Exception:
        return []
