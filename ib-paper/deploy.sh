#!/bin/bash
# Deploy MCP IB Paper Trading Server
# Owner: websurfinmurf (model environment)

set -e

cd "$(dirname "$0")"

echo "=== MCP IB Paper Trading Server ==="
echo "Port: 48012 (HTTP API)"
echo "Gateway Ports: 14001 (live socat), 14002 (paper socat), 15900 (VNC)"
echo ""

# Load secrets
if [ -f "$HOME/secrets/mcp-ib-paper.env" ]; then
    set -a
    source "$HOME/secrets/mcp-ib-paper.env"
    set +a
else
    echo "ERROR: Secrets file not found: $HOME/secrets/mcp-ib-paper.env"
    exit 1
fi

# Build and start
docker compose build
docker compose up -d

echo ""
echo "=== Deployment complete ==="
echo "Health check: curl http://localhost:48012/health"
echo "MCP endpoint: http://localhost:48012/mcp"
echo "VNC access: vnc://localhost:15900"
