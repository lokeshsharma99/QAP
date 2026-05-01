"""
Diagnose ADO MCP connection failure in FastAPI lifespan context.
Simulates the full AgentOS mcp_lifespan: GitHub MCP first, then ADO MCP.
Run inside container: python3 /app/scripts/test_ado_lifespan.py
"""
import base64
import os
import sys
import traceback

sys.path.insert(0, "/app")

import agno.tools.mcp.mcp as mm

orig_conn = mm.MCPTools._connect


async def patched_conn(self):
    try:
        await orig_conn(self)
    except BaseException as e:
        prefix = getattr(self, 'tool_name_prefix', '?')
        print(f"=== _connect EXCEPTION [{prefix}]: {type(e).__name__}: {str(e)[:400]}", flush=True)
        traceback.print_exc()
        raise


mm.MCPTools._connect = patched_conn

from contextlib import asynccontextmanager  # noqa: E402

from agno.tools.mcp import MCPTools  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from mcp.client.stdio import StdioServerParameters  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

# --- ADO MCP ---
ado_pat = os.getenv("AZURE_DEVOPS_EXT_PAT", "")
ado_email = os.getenv("AZURE_DEVOPS_EMAIL", "")
b64_pat = base64.b64encode(f"{ado_email}:{ado_pat}".encode()).decode()
ado_env = {**os.environ, "PERSONAL_ACCESS_TOKEN": b64_pat}
ado_params = StdioServerParameters(
    command="npx",
    args=["-y", "@azure-devops/mcp", "QEA", "--authentication", "pat", "-d", "core", "pipelines", "repositories", "work-items"],
    env=ado_env,
)
ado_toolkit = MCPTools(server_params=ado_params, transport="stdio", tool_name_prefix="ado_", timeout_seconds=30)

# --- GitHub MCP ---
github_token = os.getenv("GITHUB_TOKEN", "")
gh_env = {
    **os.environ,
    "GITHUB_PERSONAL_ACCESS_TOKEN": github_token,
    "GITHUB_TOOLSETS": "repos,pull_requests,issues,actions,contexts",
}
gh_params = StdioServerParameters(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-github"],
    env=gh_env,
)
gh_toolkit = MCPTools(server_params=gh_params, transport="stdio", tool_name_prefix="gh_", timeout_seconds=30)


@asynccontextmanager
async def lifespan(app):
    # Simulate agno mcp_lifespan: connect all MCP tools in order
    all_tools = [gh_toolkit, ado_toolkit]
    for tool in all_tools:
        prefix = getattr(tool, 'tool_name_prefix', '?')
        print(f"=== connecting [{prefix}]...", flush=True)
        await tool.connect()
        print(f"=== [{prefix}] tools: {len(tool.functions)}", flush=True)
    yield
    for tool in reversed(all_tools):
        await tool.close()
    print("=== LIFESPAN END", flush=True)


app = FastAPI(lifespan=lifespan)

print("=== Starting TestClient (GitHub + ADO)...", flush=True)
try:
    with TestClient(app):
        print("=== App running", flush=True)
    print("=== Done", flush=True)
except Exception as e:
    print(f"=== TestClient EXCEPTION: {type(e).__name__}: {e}", flush=True)
    traceback.print_exc()
