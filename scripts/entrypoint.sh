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
