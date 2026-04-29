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

from agno.tools.mcp import MCPTools
from mcp.client.stdio import StdioServerParameters

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _make_playwright_mcp(tool_name_prefix: str) -> list:
    """
    Build an MCPTools instance connecting to the Playwright MCP server.

    Returns an empty list when configuration is missing so agents load cleanly.

    Parameters
    ----------
    tool_name_prefix:
        Short prefix prepended to every exposed tool name to avoid collisions
        when multiple MCPTools instances are added to the same agent.
        E.g. "pw_disc_" → browser_snapshot becomes pw_disc_browser_snapshot.
    """
    mcp_url = os.getenv("PLAYWRIGHT_MCP_URL", "").rstrip("/")

    if mcp_url:
        # ---------------------------------------------------------------------------
        # Mode 1 — Connect to the running playwright-mcp Docker service via HTTP
        # Playwright MCP server exposes a Streamable-HTTP MCP endpoint at /mcp
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
        # Mode 2 — Spawn the MCP server in-process via npx (no extra service needed)
        # --headless and --no-sandbox make it work inside Docker / CI containers.
        # ---------------------------------------------------------------------------
        _log.info(
            "Playwright MCP: PLAYWRIGHT_MCP_URL not set — running headless via npx stdio. "
            "To use the dedicated service, start it with: "
            "docker compose --profile mcp up -d"
        )
        return [
            MCPTools(
                server_params=StdioServerParameters(
                    command="npx",
                    args=[
                        "-y",
                        "@playwright/mcp@latest",
                        "--headless",
                        "--no-sandbox",
                        "--isolated",
                    ],
                    env={**os.environ},
                ),
                transport="stdio",
                tool_name_prefix=tool_name_prefix,
            )
        ]


# ---------------------------------------------------------------------------
# Per-agent factory functions
# ---------------------------------------------------------------------------

def get_playwright_mcp_for_discovery() -> list:
    """
    Playwright MCP tools for the Discovery agent.

    Discovery uses these to crawl the AUT in a real browser, capture
    accessibility snapshots of each page/component, and build the Site Manifesto.
    Full read-write access: navigate, click, snapshot, screenshot.
    """
    return _make_playwright_mcp(tool_name_prefix="pw_disc_")


def get_playwright_mcp_for_medic() -> list:
    """
    Playwright MCP tools for the Medic agent.

    Medic uses these after applying a healing patch to verify the fixed locator
    resolves correctly on the live AUT.
    Primarily read-only: navigate + snapshot.
    """
    return _make_playwright_mcp(tool_name_prefix="pw_med_")
