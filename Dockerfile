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
# NOTE: Chromium browser binaries are NOT baked into this image.
# In Docker deployments use the dedicated playwright-mcp service (SSE transport)
# started via: docker compose --profile mcp up -d
# The PLAYWRIGHT_MCP_URL env var in compose.yaml points agents to that service.
# For local / stdio fallback, install Chromium separately with:
#   npx playwright install chromium --with-deps
# ---------------------------------------------------------------------------
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

RUN npm install -g \
        @modelcontextprotocol/server-github \
        @azure-devops/mcp \
        mcp-remote \
        @playwright/mcp@latest && \
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
RUN uv pip sync requirements.txt --system && \
    pip install ruff --quiet

# ---------------------------------------------------------------------------
# Automation framework — Node.js dependencies
# Copy manifests before COPY . . so this layer is cached across code changes.
# --ignore-scripts skips the preinstall playwright browser download
# (browsers live in the dedicated playwright-mcp sidecar, not here).
# automation/node_modules/ is in .dockerignore so COPY . . won't clobber this.
# ---------------------------------------------------------------------------
COPY automation/package.json automation/package-lock.json ./automation/
RUN cd /app/automation && npm install --ignore-scripts --no-audit --no-fund && npm cache clean --force

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
# Agno framework patches
# ---------------------------------------------------------------------------
# Patch get_team_member_interactions_str to guard against None run_response.
# This can happen when a member agent's run is blocked by a guardrail (e.g.
# PII detection), the stream ends without yielding a RunOutput, and None is
# stored as the interaction's run_response. The next delegation then crashes
# at interaction["run_response"].to_dict(). See: agno/utils/team.py
RUN python3 /app/scripts/patch_agno_team_utils.py

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
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
