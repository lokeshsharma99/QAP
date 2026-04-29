"""
app/endpoints/mcp_status.py
============================

Health-check endpoint for the three MCP Docker services:
  GET /mcp/status  →  TCP probe + registered tool counts per service

Used by the Settings UI to show live green/red status for each MCP integration.
"""

import os
import socket
import urllib.parse

from fastapi import APIRouter

router = APIRouter(prefix="/mcp", tags=["mcp"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tcp_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_host_port(url: str, default_host: str, default_port: int) -> tuple[str, int]:
    parsed = urllib.parse.urlparse(url)
    return (parsed.hostname or default_host, parsed.port or default_port)


def _count_tools(singleton) -> int:
    """Safely count registered tools on an MCPTools singleton."""
    try:
        if singleton is None:
            return 0
        fns = getattr(singleton, "functions", None)
        if isinstance(fns, dict):
            return len(fns)
        if isinstance(fns, list):
            return len(fns)
        return 0
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.get("/status")
async def mcp_status():
    """
    Returns TCP reachability + tool count for GitHub, ADO, and Playwright MCP services.

    Response shape:
    {
        "services": {
            "github":     { name, url, reachable, tools, configured, agents },
            "ado":        { ... },
            "playwright": { ... },
        }
    }
    """
    github_url = os.getenv("GITHUB_MCP_URL", "http://github-mcp:8080")
    ado_url = os.getenv("ADO_MCP_URL", "http://ado-mcp:8932/mcp")
    playwright_url = os.getenv("PLAYWRIGHT_MCP_URL", "http://playwright-mcp:8931/mcp")

    gh_host, gh_port = _parse_host_port(github_url, "github-mcp", 8080)
    ado_host, ado_port = _parse_host_port(ado_url, "ado-mcp", 8932)
    pw_host, pw_port = _parse_host_port(playwright_url, "playwright-mcp", 8931)

    gh_reachable = _tcp_reachable(gh_host, gh_port)
    ado_reachable = _tcp_reachable(ado_host, ado_port)
    pw_reachable = _tcp_reachable(pw_host, pw_port)

    # Tool counts come from already-initialized singletons — no reconnect overhead
    gh_tools = 0
    ado_tools = 0
    pw_tools = 0

    try:
        from app.github_mcp import _GITHUB_MCP_SINGLETON  # noqa: PLC0415
        gh_tools = _count_tools(_GITHUB_MCP_SINGLETON)
    except Exception:
        pass

    try:
        from app.ado_mcp import _ADO_MCP_SINGLETON  # noqa: PLC0415
        ado_tools = _count_tools(_ADO_MCP_SINGLETON)
    except Exception:
        pass

    try:
        from app.playwright_mcp import _PLAYWRIGHT_MCP_SINGLETON  # noqa: PLC0415
        if isinstance(_PLAYWRIGHT_MCP_SINGLETON, list) and _PLAYWRIGHT_MCP_SINGLETON:
            pw_tools = _count_tools(_PLAYWRIGHT_MCP_SINGLETON[0])
        else:
            pw_tools = _count_tools(_PLAYWRIGHT_MCP_SINGLETON)
    except Exception:
        pass

    github_token = os.getenv("GITHUB_TOKEN", "")
    ado_url_env = os.getenv("AZURE_DEVOPS_URL", "")
    ado_pat = os.getenv("AZURE_DEVOPS_PAT") or os.getenv("AZURE_DEVOPS_EXT_PAT", "")

    return {
        "services": {
            "github": {
                "name": "GitHub MCP",
                "url": github_url,
                "reachable": gh_reachable,
                "tools": gh_tools,
                "configured": bool(github_token),
                "agents": ["architect", "discovery", "engineer", "detective", "pipeline_analyst", "impact_analyst"],
            },
            "ado": {
                "name": "Azure DevOps MCP",
                "url": ado_url,
                "reachable": ado_reachable,
                "tools": ado_tools,
                "configured": bool(ado_url_env and ado_pat),
                "agents": ["pipeline_analyst", "ci_log_analyzer", "architect"],
            },
            "playwright": {
                "name": "Playwright MCP",
                "url": playwright_url,
                "reachable": pw_reachable,
                "tools": pw_tools,
                "configured": True,
                "agents": ["discovery", "medic"],
            },
        }
    }
