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
if [ -f "$HOME/projects/secrets/mcp-ib-paper.env" ]; then
    set -a
    source "$HOME/projects/secrets/mcp-ib-paper.env"
    set +a
else
    echo "ERROR: Secrets file not found: $HOME/projects/secrets/mcp-ib-paper.env"
    exit 1
fi

# Build the wrapper (mcp-ib-paper) — always safe to rebuild
docker compose build mcp-ib-paper

# Start/restart the wrapper — recreate is safe (no persistent state)
docker compose up -d mcp-ib-paper

# Gateway: prefer start over recreate to preserve IB API settings (ibg.xml)
# The "Allow connections from localhost only" setting is stored in encrypted
# ibg.xml which survives docker start/stop but NOT container recreation.
# Only recreate gateway with --rebuild flag.
if [[ "${1:-}" == "--rebuild" ]]; then
    echo ""
    echo "⚠️  --rebuild: Recreating gateway (IB API settings will be lost!)"
    echo "   VNC fix will be required after: linuxserver.lan:15900"
    docker compose build mcp-ib-gateway-paper
    docker compose up -d mcp-ib-gateway-paper
else
    # Just ensure it's running (no recreate)
    if docker ps --format '{{.Names}}' | grep -q mcp-ib-gateway-paper; then
        echo "Gateway already running — not recreating (preserves IB API settings)"
        echo "Use './deploy.sh --rebuild' to force gateway recreation"
    else
        echo "Gateway not running — starting"
        docker compose up -d mcp-ib-gateway-paper
    fi
fi

echo ""
echo "=== Deployment complete ==="
echo "Health check: curl http://localhost:48012/health"
echo "MCP endpoint: http://localhost:48012/mcp"
echo "VNC access: vnc://localhost:15900"
echo ""
echo "Note: If gateway was rebuilt, VNC fix may be needed:"
echo "  1. VNC → linuxserver.lan:15900"
echo "  2. Configure → Settings → API → Uncheck 'localhost only'"
