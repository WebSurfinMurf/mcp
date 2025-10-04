#!/bin/bash

# Deploy IB MCP Server with IB Gateway
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Deploying IB MCP Server with IB Gateway..."

# Check if env file exists
if [ ! -f /home/administrator/projects/secrets/mcp-ib.env ]; then
    echo "Error: /home/administrator/projects/secrets/mcp-ib.env not found."
    echo "Please copy .env.example to /home/administrator/projects/secrets/mcp-ib.env and configure it."
    exit 1
fi

# Create necessary directories
mkdir -p jts ibc config

# Build and start services
docker compose build
docker compose down
docker compose up -d

echo "IB MCP Server deployed successfully!"
echo ""
echo "Services available:"
echo "  - IB Gateway Paper: localhost:14002"
echo "  - IB Gateway Live:  localhost:14001"
echo "  - VNC (GUI):        localhost:15900"
echo "  - MCP Server:       localhost:3000"
echo ""
echo "To use with Claude Code, add to your MCP config:"
echo "  codex mcp add mcp-ib docker exec -i mcp-ib python -m ib_mcp.server --host mcp-ib-gateway --port 4002"
echo ""
echo "Check logs with: docker compose logs -f"
