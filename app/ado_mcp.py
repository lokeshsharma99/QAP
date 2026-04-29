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

from agno.tools.mcp import MCPTools
from mcp.client.stdio import StdioServerParameters

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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
# Singleton — one shared ADO MCP process for all agents.
# Using a single instance avoids spawning multiple npx processes at startup.
# All domains needed by any agent are included in the superset.
# Returns [] when AZURE_DEVOPS_URL or AZURE_DEVOPS_PAT are not configured so
# that no MCPTools object is registered with AgentOS and no startup auth
# attempt is made in headless / Docker environments.
# ---------------------------------------------------------------------------
_ADO_MCP_SINGLETON: MCPTools | None = None


def _get_ado_mcp_singleton() -> list:
    """Return singleton list, empty if URL or EXT_PAT are not configured.

    The @azure-devops/mcp npm package reads AZURE_DEVOPS_EXT_PAT for
    non-interactive PAT auth.  We require this variable to be set explicitly
    (not AZURE_DEVOPS_PAT, which is a generic convention but not what the npm
    package reads).  Without it the server falls back to browser-based
    interactive auth which hangs and fails in headless Docker containers.
    """
    ado_url = os.getenv("AZURE_DEVOPS_URL", "").rstrip("/")
    # @azure-devops/mcp reads AZURE_DEVOPS_EXT_PAT natively.
    # Require it to be set explicitly; do NOT fall back to AZURE_DEVOPS_PAT so
    # that we can detect the "PAT set but wrong variable name" misconfiguration.
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
            "Set AZURE_DEVOPS_EXT_PAT=<your-pat> in .env. "
            "The @azure-devops/mcp package reads this variable for non-interactive auth. "
            "Without it the server falls back to browser auth which fails in headless Docker."
        )
        return []

    global _ADO_MCP_SINGLETON
    if _ADO_MCP_SINGLETON is None:
        _ADO_MCP_SINGLETON = _make_ado_mcp(
            domains=["core", "pipelines", "repositories", "work-items"],
            tool_name_prefix="ado_",
        )
    return [_ADO_MCP_SINGLETON]


# ---------------------------------------------------------------------------
# Per-agent factory functions
# Each returns a list so agents can unpack: tools=[..., *get_ado_mcp_for_X()]
# Returns [] when AZURE_DEVOPS_URL / AZURE_DEVOPS_PAT are not configured.
# ---------------------------------------------------------------------------

def get_ado_mcp_for_pipeline_analyst() -> list:
    """
    ADO MCP tools for the Pipeline Analyst agent.

    Domains: core, pipelines, repositories.

    Pipeline Analyst uses these to:
    - List and inspect ADO pipeline runs across projects
    - Download job / step logs for failed pipeline runs
    - Read recent commits and diffs correlated with the failure
    - Fetch build definitions and pipeline YAML configuration
    - Compare the current run against the last passing run
    """
    return _get_ado_mcp_singleton()


def get_ado_mcp_for_ci_log_analyzer() -> list:
    """
    ADO MCP tools for the CI Log Analyzer agent.

    Domains: core, pipelines, work-items.

    CI Log Analyzer uses these to:
    - Fetch pipeline run logs and test results for RCA analysis
    - Read the timeline / step breakdown of failed builds
    - Create ADO work items (bugs / tasks) after HITL approval
    - Update existing work items with RCA findings and remediation notes
    - Search for duplicate open bugs before creating new ones
    """
    return _get_ado_mcp_singleton()


def get_ado_mcp_for_architect() -> list:
    """
    ADO MCP tools for the Architect agent.

    Domains: core, work-items.

    Architect uses these to:
    - Fetch ADO work items (User Stories, Bugs, Tasks) as requirements
    - Read acceptance criteria from work item descriptions
    - Read linked test cases to understand existing coverage
    - Query sprint / backlog for priority context before producing Execution Plan
    """
    return _get_ado_mcp_singleton()
