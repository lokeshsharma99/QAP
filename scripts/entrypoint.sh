#!/bin/bash

############################################################################
#
#    Quality Autopilot — Container Entrypoint
#
############################################################################

# Colors
ORANGE='\033[38;5;208m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${ORANGE}"
cat << 'BANNER'
     ____    _    ____
    / __ \  / \  |  _ \
   | |  | |/ _ \ | |_) |
   | |__| / ___ \|  __/
    \___/_/   \_\_|

    Quality Autopilot
    Agentic STLC Compiler
BANNER
echo -e "${NC}"

if [[ "${PRINT_ENV_ON_LOAD,,}" = true ]]; then
    echo -e "    ${DIM}Environment:${NC}"
    printenv | sed 's/^/    /'
    echo ""
fi

if [[ "${WAIT_FOR_DB,,}" = true ]]; then
    echo -e "    ${DIM}Waiting for database at ${DB_HOST}:${DB_PORT}...${NC}"
    dockerize -wait tcp://$DB_HOST:$DB_PORT -timeout 300s
    echo -e "    ${BOLD}Database ready.${NC}"
    echo ""
fi

# ---------------------------------------------------------------------------
# Optional: drop + recreate all vector/KB tables.
# Set RECREATE_VECTOR_TABLES=1 on one restart after switching EMBEDDING_PROVIDER
# (e.g. from ollama/2560-dim to openai/1536-dim). The tables are empty in that
# case, so dropping is safe. Unset the env var on the next deploy to prevent
# accidental data loss.
# ---------------------------------------------------------------------------
if [[ "${RECREATE_VECTOR_TABLES}" = "1" || "${RECREATE_VECTOR_TABLES,,}" = "true" ]]; then
    echo -e "    ${DIM}RECREATE_VECTOR_TABLES=1 — dropping vector tables for provider switch...${NC}"
    python - <<'PYEOF'
import psycopg, os
from urllib.parse import quote

user     = os.getenv("DB_USER",     "ai")
password = quote(os.getenv("DB_PASS", "ai"), safe="")
host     = os.getenv("DB_HOST",     "localhost")
port     = os.getenv("DB_PORT",     "5432")
database = os.getenv("DB_DATABASE", "ai")

dsn = f"host={host} port={port} dbname={database} user={user} password={os.getenv('DB_PASS','ai')}"
tables = [
    "qap_learnings",          "qap_learnings_contents",
    "codebase_vectors",       "codebase_vectors_contents",
    "site_manifesto_vectors", "site_manifesto_vectors_contents",
    "rca_vectors",            "rca_vectors_contents",
    "test_results_vectors",   "test_results_vectors_contents",
    "document_library_vectors","document_library_vectors_contents",
    "rtm_vectors",            "rtm_vectors_contents",
]
try:
    conn = psycopg.connect(dsn)
    cur  = conn.cursor()
    for t in tables:
        cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
        print(f"      dropped {t}")
    conn.commit()
    conn.close()
    print("    Vector tables reset — will be recreated with correct dimensions on first use.")
except Exception as ex:
    print(f"    WARNING: could not reset vector tables: {ex}")
PYEOF
    echo ""
fi

# Allow the app user to access the Docker socket (needed for Docker MCP Gateway).
# Only applied when the socket is mounted — safe because the container is already
# trusted to run docker commands by virtue of the socket being mounted.
if [ -S /var/run/docker.sock ]; then
    chmod 666 /var/run/docker.sock 2>/dev/null || true
fi

case "$1" in
    chill)
        echo -e "    ${DIM}Mode: chill${NC}"
        echo -e "    ${BOLD}Container running.${NC}"
        echo ""
        while true; do sleep 18000; done
        ;;
    *)
        echo -e "    ${DIM}> $@${NC}"
        echo ""
        exec "$@"
        ;;
esac
