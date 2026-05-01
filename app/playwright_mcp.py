"""
app/playwright_mcp.py
=====================

Factory functions returning Agno MCPTools instances wired to the official
Microsoft Playwright MCP server (@playwright/mcp).

Transport strategy
------------------
Two modes are supported, selected automatically at import time:

1. **SSE / Streamable-HTTP service** (preferred in Docker):
   Set PLAYWRIGHT_MCP_URL in .env (e.g. http://playwright-mcp:8931).
   The compose.yaml already sets this when the playwright-mcp service is up.
   Start the service with: ``docker compose --profile mcp up -d``

2. **Stdio / in-process** (fallback — zero extra services needed):
   When PLAYWRIGHT_MCP_URL is not set, spawns the MCP server directly via:
   ``npx -y @playwright/mcp@latest --headless --no-sandbox``
   Node.js is already installed in the qap-api image, so this works out of
   the box without starting the playwright-mcp container.

Playwright MCP Tools (core — always loaded):
  browser_navigate          — go to a URL
  browser_snapshot          — accessibility snapshot (no vision model needed)
  browser_click             — click an element
  browser_type              — type text into an input
  browser_fill_form         — fill multiple fields at once
  browser_select_option     — pick a dropdown option
  browser_hover             — hover over an element
  browser_take_screenshot   — capture a screenshot (read-only)
  browser_wait_for          — wait for text / element
  browser_network_requests  — list network requests
  browser_evaluate          — run JavaScript on the page
  browser_resize            — resize the viewport
  browser_tabs              — manage browser tabs
  browser_close             — close the browser/page

Usage by agent
--------------
  Discovery — full browser crawl of the AUT to generate the Site Manifesto.
              Uses navigate + snapshot + click to map pages and components.
  Medic     — opens the live AUT after a healing patch to verify the fixed
              locator resolves correctly.  Read-only: snapshot + navigate.
"""

import logging
import os
import socket
import urllib.parse

from agno.utils.log import log_warning

from agno.tools.mcp import MCPTools

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _playwright_mcp_reachable(url: str) -> bool:
    """Return True if the playwright-mcp service TCP port is open."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or "playwright-mcp"
    port = parsed.port or 8931
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def _make_playwright_mcp(tool_name_prefix: str) -> list:
    """
    Build an MCPTools instance connecting to the Playwright MCP server.

    Returns an empty list when PLAYWRIGHT_MCP_URL is not set or the
    service is not reachable (container not running).

    Start the service with:
        docker compose --profile mcp up -d

    Parameters
    ----------
    tool_name_prefix:
        Short prefix prepended to every exposed tool name to avoid collisions
        when multiple MCPTools instances are added to the same agent.
        E.g. "pw_disc_" → browser_snapshot becomes pw_disc_browser_snapshot.
    """
    mcp_url = os.getenv("PLAYWRIGHT_MCP_URL", "").rstrip("/")

    if mcp_url:
        # Pre-flight: verify the service TCP port is open before registering tools.
        # This avoids a "Failed to initialize MCP toolkit" error at startup when
        # the playwright-mcp container is not running (common in dev environments).
        if not _playwright_mcp_reachable(mcp_url):
            log_warning(
                "PLAYWRIGHT_MCP_URL is set to %s but the service is not reachable. "
                "Playwright MCP tools are unavailable. "
                "Start the service with: docker compose up -d playwright-mcp",
                mcp_url,
            )
            return []
        # ---------------------------------------------------------------------------
        # Mode 1 — Connect to the running playwright-mcp Docker service via HTTP.
        # This is the production path: a separate container runs the browser and
        # exposes a Streamable-HTTP MCP endpoint at /mcp.  No npx spawn in qap-api.
        # ---------------------------------------------------------------------------
        from agno.tools.mcp.params import StreamableHTTPClientParams

        _log.info("Playwright MCP: connecting to service at %s/mcp", mcp_url)
        return [
            MCPTools(
                server_params=StreamableHTTPClientParams(url=f"{mcp_url}/mcp"),
                transport="streamable-http",
                tool_name_prefix=tool_name_prefix,
            )
        ]
    else:
        # ---------------------------------------------------------------------------
        # No service URL — skip tool registration entirely.
        # Spawning @playwright/mcp via npx inside qap-api causes startup timeouts
        # and couples browser state to the API process.
        #
        # To enable Playwright MCP tools, start the dedicated service:
        #   docker compose --profile mcp up -d
        # Then set PLAYWRIGHT_MCP_URL=http://playwright-mcp:8931 in .env.
        # ---------------------------------------------------------------------------
        _log.info(
            "Playwright MCP: PLAYWRIGHT_MCP_URL not set — Playwright tools unavailable. "
            "Run 'docker compose --profile mcp up -d' and set PLAYWRIGHT_MCP_URL in .env "
            "to enable browser automation tools for Discovery and Medic."
        )
        return []


# ---------------------------------------------------------------------------
# Singleton — one shared Playwright MCP process for all agents.
# Using a single instance avoids spawning multiple headless browser processes
# at startup (which caused simultaneous connection timeouts).
# ---------------------------------------------------------------------------
_PLAYWRIGHT_MCP_SINGLETON: list | None = None


def _get_playwright_mcp_singleton() -> list:
    """Return the module-level singleton list, creating it on first call."""
    global _PLAYWRIGHT_MCP_SINGLETON
    if _PLAYWRIGHT_MCP_SINGLETON is None:
        _PLAYWRIGHT_MCP_SINGLETON = _make_playwright_mcp(tool_name_prefix="pw_")
    return _PLAYWRIGHT_MCP_SINGLETON


# ---------------------------------------------------------------------------
# Per-agent factory functions
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Per-agent tool subsets
# ---------------------------------------------------------------------------

# Discovery: full access — needs to navigate, click, type, and take snapshots
# to build the complete Site Manifesto from the live AUT.
# (None = no filtering, all 23 browser tools available)
_DISCOVERY_PLAYWRIGHT_TOOLS: list[str] | None = None

# Medic: read-only verification — after applying a locator patch, the Medic
# navigates to the page and takes a snapshot to confirm the element resolves.
# No input, form-fill, or destructive browser operations needed.
_MEDIC_PLAYWRIGHT_TOOLS: list[str] = [
    "browser_navigate",       # go to the page under test
    "browser_navigate_back",  # return to previous page if needed
    "browser_snapshot",       # capture accessibility tree to verify locator
    "browser_take_screenshot", # visual confirmation of the healed element
    "browser_wait_for",       # wait for element / text before snapshotting
    "browser_close",          # clean up browser session after verification
]


# ---------------------------------------------------------------------------
# Per-agent factory functions
# ---------------------------------------------------------------------------

def get_playwright_mcp_for_discovery() -> list:
    """
    Playwright MCP tools for the Discovery agent.

    Discovery uses these to crawl the AUT in a real browser, capture
    accessibility snapshots of each page/component, and build the Site Manifesto.
    Full read-write access: navigate, click, snapshot, screenshot, type, fill.
    """
    return _get_playwright_mcp_singleton()


def get_playwright_mcp_for_medic() -> list:
    """
    Playwright MCP tools for the Medic agent.

    Medic uses these after applying a healing patch to verify the fixed locator
    resolves correctly on the live AUT.
    Read-only subset: navigate + snapshot + screenshot only (6 tools vs 23).
    """
    mcp_url = os.getenv("PLAYWRIGHT_MCP_URL", "").rstrip("/")
    if mcp_url and _playwright_mcp_reachable(mcp_url):
        from agno.tools.mcp.params import StreamableHTTPClientParams
        return [
            MCPTools(
                server_params=StreamableHTTPClientParams(url=f"{mcp_url}/mcp"),
                transport="streamable-http",
                tool_name_prefix="pw_",
                include_tools=_MEDIC_PLAYWRIGHT_TOOLS,
            )
        ]
    # No service available — Medic cannot do live verification
    _log.info(
        "Playwright MCP unavailable — Medic live-verification disabled. "
        "Start with: docker compose --profile mcp up -d"
    )
    return []
