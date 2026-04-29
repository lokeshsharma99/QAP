# ===========================================================================
# Quality Autopilot
# ===========================================================================
# Agentic compiler for the Software Testing Life Cycle, built with Agno.
# Runs as a non-root user (app) with:
#   /app    - application code
# ===========================================================================

FROM agnohq/python:3.12

# ---------------------------------------------------------------------------
# Node.js LTS — required for MCP servers (GitHub, ADO, Atlassian, Playwright)
# Uses the official NodeSource setup script so the version is pinned via apt.
# ---------------------------------------------------------------------------
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends curl ca-certificates gnupg lsb-release && \
    # Node.js LTS
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    # Docker CLI (for `docker mcp gateway run` — Docker MCP Gateway support)
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list && \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends docker-ce-cli && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    node --version && npm --version && docker --version

# ---------------------------------------------------------------------------
# Pre-install all MCP servers globally
# Eliminates first-run npx download latency and pins versions at build time.
#
#   @modelcontextprotocol/server-github  — GitHub MCP (Architect, Discovery, Engineer, Detective …)
#   @azure-devops/mcp                    — Azure DevOps MCP (Pipeline Analyst, CI Log Analyzer, Architect)
#   mcp-remote                           — Atlassian Rovo MCP proxy (Architect, Scribe, CI Log Analyzer)
#   @playwright/mcp                      — Playwright MCP (Discovery, Medic)
#
# Playwright Chromium is also installed with its system-level dependencies so
# the headless npx stdio mode works inside the container without a separate
# playwright-mcp service.  Browser binaries land in PLAYWRIGHT_BROWSERS_PATH.
# ---------------------------------------------------------------------------
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/local/ms-playwright

RUN npm install -g \
        @modelcontextprotocol/server-github \
        @azure-devops/mcp \
        mcp-remote \
        @playwright/mcp@latest && \
    npx playwright install chromium --with-deps && \
    chmod -R 755 /usr/local/ms-playwright && \
    npm cache clean --force

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# ---------------------------------------------------------------------------
# Create non-root user
# ---------------------------------------------------------------------------
RUN groupadd -r app && useradd -r -g app -m -s /bin/bash app

# ---------------------------------------------------------------------------
# Application code
# ---------------------------------------------------------------------------
WORKDIR /app
COPY requirements.txt .
RUN uv pip sync requirements.txt --system

# ---------------------------------------------------------------------------
# Patch agno library: PostgresDb.get_all_memory_topics() does not accept
# user_id kwarg — strip it so /memory_topics returns 200 instead of 500.
# ---------------------------------------------------------------------------
RUN sed -i \
    's/db\.get_all_memory_topics(user_id=user_id)/db.get_all_memory_topics()/g' \
    /usr/local/lib/python3.12/site-packages/agno/os/routers/memory/memory.py

# ---------------------------------------------------------------------------
# Patch agno library: MCP tool "Not Found" errors are logged as full
# exception tracebacks (log_exception) even though they are handled
# gracefully and the agent receives a clean error string.
# Downgrade to log_warning so the logs are not polluted with tracebacks
# every time a GitHub MCP tool reads a resource that does not exist yet.
# Step 1: add log_warning to the import so the symbol is available.
# Step 2: replace the log_exception call with log_warning.
# ---------------------------------------------------------------------------
RUN sed -i \
    's/from agno.utils.log import log_debug, log_exception/from agno.utils.log import log_debug, log_exception, log_warning/' \
    /usr/local/lib/python3.12/site-packages/agno/utils/mcp.py && \
    sed -i \
    's/log_exception(f"Failed to call MCP tool/log_warning(f"MCP tool not found (non-fatal):/g' \
    /usr/local/lib/python3.12/site-packages/agno/utils/mcp.py

COPY . .

# ---------------------------------------------------------------------------
# Directory setup & permissions
# ---------------------------------------------------------------------------
RUN chmod 755 /app

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
RUN chmod +x /app/scripts/entrypoint.sh
ENTRYPOINT ["/app/scripts/entrypoint.sh"]

# ---------------------------------------------------------------------------
# Switch to non-root user
# ---------------------------------------------------------------------------
USER app
WORKDIR /app

EXPOSE 8000

# ---------------------------------------------------------------------------
# Default command (overridden by compose)
# ---------------------------------------------------------------------------
CMD ["chill"]
