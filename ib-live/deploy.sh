#!/bin/bash
# Deploy MCP IB Live Trading Server
# Owner: administrator (production environment)
# NOTE: Currently configured for PAPER trading mode for testing

set -e

cd "$(dirname "$0")"

echo "=== MCP IB Live Trading Server ==="
echo "WARNING: Currently configured for PAPER trading (for testing)"
echo "Port: 48014 (HTTP API)"
echo "Gateway Ports: 14011 (live socat), 14012 (paper socat), 15901 (VNC)"
echo ""

# Load secrets
if [ -f "$HOME/secrets/mcp-ib-live.env" ]; then
    set -a
    source "$HOME/secrets/mcp-ib-live.env"
    set +a
else
    echo "ERROR: Secrets file not found: $HOME/secrets/mcp-ib-live.env"
    exit 1
fi

# Build and start
docker compose build
docker compose up -d

echo ""
echo "=== Deployment complete ==="
echo "Health check: curl http://localhost:48014/health"
echo "MCP endpoint: http://localhost:48014/mcp"
echo "VNC access: vnc://localhost:15901"
