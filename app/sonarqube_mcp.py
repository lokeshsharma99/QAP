"""
app/sonarqube_mcp.py
====================

Factory for Agno MCPTools wired to the SonarQube MCP server.

The SonarQube MCP server (@sonarsource/mcp-server-sonarqube) is wrapped via
supergateway and exposed as a Streamable-HTTP endpoint on port 9001.

Start with:
    docker compose --profile sonar up -d

Then agents can call tools like:
    sonarqube_get_quality_gate_status — quality gate pass/fail
    sonarqube_get_project_issues      — bugs, vulnerabilities, code smells
    sonarqube_get_metrics             — coverage, duplication, complexity

If SONAR_MCP_URL is not set or the server is unreachable, returns an empty
list so agents continue without Sonar tooling (graceful degradation).
"""

from __future__ import annotations

import logging
from os import getenv

logger = logging.getLogger(__name__)

# URL of the SonarQube MCP server (supergateway wrapping @sonarsource/mcp-server-sonarqube)
_SONAR_MCP_URL = getenv("SONAR_MCP_URL", "http://localhost:9001/mcp")


def get_sonarqube_mcp_tools() -> list:
    """Return Agno MCPTools connected to the SonarQube MCP server.

    Returns an empty list if:
    - SONAR_MCP_URL is not set
    - SONAR_TOKEN is not set (SonarQube requires a token)
    - The MCP server is not reachable

    Call from Judge and Engineer agents:
        from app.sonarqube_mcp import get_sonarqube_mcp_tools
        _sonar_tools = get_sonarqube_mcp_tools()
    """
    sonar_token = getenv("SONAR_TOKEN", "")
    if not sonar_token:
        logger.debug("SONAR_TOKEN not set — SonarQube MCP tools not loaded")
        return []

    try:
        from agno.tools.mcp import MCPTools

        tools = MCPTools(
            url=_SONAR_MCP_URL,
            transport="streamable-http",
        )
        logger.info("SonarQube MCP tools loaded from %s", _SONAR_MCP_URL)
        return [tools]
    except Exception as exc:
        logger.debug("SonarQube MCP not available (%s) — continuing without it", exc)
        return []
