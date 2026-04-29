# ===========================================================================
# Quality Autopilot
# ===========================================================================
# Agentic compiler for the Software Testing Life Cycle, built with Agno.
# Runs as a non-root user (app) with:
#   /app    - application code
# ===========================================================================

FROM agnohq/python:3.12

# ---------------------------------------------------------------------------
# Node.js LTS — required for GitHub MCP server (npx @modelcontextprotocol/server-github)
# Uses the official NodeSource setup script so the version is pinned via apt.
# ---------------------------------------------------------------------------
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    node --version && npm --version

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
# ---------------------------------------------------------------------------
RUN sed -i \
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
