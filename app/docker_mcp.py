"""
app/docker_mcp.py
=================

Factory returning an Agno MCPTools instance wired to Docker MCP Gateway.

Docker MCP Gateway aggregates every MCP extension configured in Docker Desktop
into a single stdio transport — replacing the individual npx processes for
GitHub, ADO, Atlassian, Playwright etc. with one connection.

Requirements
------------
- Docker Desktop 4.40+ with MCP Toolkit enabled.
- `docker` CLI must be available on PATH inside the container.
  (The Dockerfile installs the Docker CLI for this purpose.)
- The host Docker socket must be mounted into the container so the `docker`
  command can reach Docker Desktop's daemon:
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

Usage
-----
Set DOCKER_MCP_PROFILE in .env to activate the gateway:

    DOCKER_MCP_PROFILE=default          # use Docker Desktop default profile
    # DOCKER_MCP_PROFILE=               # unset = gateway disabled (fallback to npx)

When the profile is set the gateway singleton is registered with AgentOS and
ALL configured Docker MCP tools (GitHub, ADO, Atlassian, Playwright, etc.)
are available to every agent through a single MCPTools connection.

When the profile is NOT set the module returns [] so AgentOS registers nothing
and the individual npx-based singletons in github_mcp.py / ado_mcp.py / etc.
are used as normal.
"""

import logging
import os

from agno.tools.mcp import MCPTools
from agno.utils.log import log_warning
from mcp.client.stdio import StdioServerParameters

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton — one Docker MCP Gateway process shared across all agents.
# ---------------------------------------------------------------------------
_DOCKER_MCP_SINGLETON: MCPTools | None = None


def _docker_mcp_gateway_available() -> bool:
    """Check if the docker-mcp CLI plugin binary is installed.

    `docker mcp` is a Docker Desktop CLI plugin stored as a binary named
    `docker-mcp` in one of Docker's standard plugin directories.  The
    `docker mcp gateway --help` trick does NOT work because docker silently
    falls back to its own generic help (exit 0) when the plugin is missing.
    Checking the binary directly is reliable and avoids a subprocess fork.
    """
    plugin_dirs = [
        "/usr/local/lib/docker/cli-plugins",
        "/usr/lib/docker/cli-plugins",
        os.path.expanduser("~/.docker/cli-plugins"),
    ]
    return any(
        os.path.isfile(os.path.join(d, "docker-mcp"))
        for d in plugin_dirs
    )


def _get_docker_mcp_singleton() -> list:
    """Return [singleton], or [] when DOCKER_MCP_PROFILE is not set."""
    profile = os.getenv("DOCKER_MCP_PROFILE", "").strip()

    if not profile:
        return []

    if not _docker_mcp_gateway_available():
        log_warning(
            "DOCKER_MCP_PROFILE is set but the docker-mcp CLI plugin is not installed. "
            "The plugin ships with Docker Desktop ≥ 4.40 (MCP Toolkit). "
            "Docker MCP Gateway is disabled — individual npx MCP servers are used instead."
        )
        return []

    global _DOCKER_MCP_SINGLETON
    if _DOCKER_MCP_SINGLETON is None:
        _log.info(
            f"Docker MCP Gateway enabled — profile: '{profile}'. "
            "All Docker MCP Toolkit extensions will be available."
        )
        _DOCKER_MCP_SINGLETON = MCPTools(
            server_params=StdioServerParameters(
                command="docker",
                args=["mcp", "gateway", "run", "--profile", profile],
            ),
            transport="stdio",
            timeout_seconds=30,
        )
    return [_DOCKER_MCP_SINGLETON]


# ---------------------------------------------------------------------------
# Public API — one function per logical concern so callers stay readable.
# All functions return the same singleton list (or [] when disabled).
# ---------------------------------------------------------------------------

def get_docker_mcp_for_github() -> list:
    """
    Docker MCP Gateway tools — GitHub toolset.

    Exposes all GitHub MCP tools configured in Docker Desktop's MCP Toolkit.
    Returns [] when DOCKER_MCP_PROFILE is not set (npx fallback is used).
    """
    return _get_docker_mcp_singleton()


def get_docker_mcp_for_ado() -> list:
    """
    Docker MCP Gateway tools — Azure DevOps toolset.

    Exposes all ADO MCP tools configured in Docker Desktop's MCP Toolkit.
    Returns [] when DOCKER_MCP_PROFILE is not set (npx fallback is used).
    """
    return _get_docker_mcp_singleton()


def get_docker_mcp_for_atlassian() -> list:
    """
    Docker MCP Gateway tools — Atlassian toolset.

    Exposes Jira / Confluence tools configured in Docker Desktop's MCP Toolkit.
    Returns [] when DOCKER_MCP_PROFILE is not set (npx fallback is used).
    """
    return _get_docker_mcp_singleton()


def get_docker_mcp_for_playwright() -> list:
    """
    Docker MCP Gateway tools — Playwright browser toolset.

    Exposes Playwright browser automation tools via Docker MCP Toolkit.
    Returns [] when DOCKER_MCP_PROFILE is not set (npx fallback is used).
    """
    return _get_docker_mcp_singleton()


def get_docker_mcp_tools() -> list:
    """
    Return the full Docker MCP Gateway singleton for use in any agent.

    Use this when you want access to ALL Docker MCP Toolkit tools at once.
    Returns [] when DOCKER_MCP_PROFILE is not set.
    """
    return _get_docker_mcp_singleton()
