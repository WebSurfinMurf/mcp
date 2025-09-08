#!/bin/bash
# Deploy MCP SSE Proxy with network isolation
# Uses docker-compose for better management
set -e

PROJECT_NAME="mcp-proxy"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== MCP SSE Proxy Deployment ==="
echo "Mode: Network Isolated (litellm-net only)"
echo "Security: No exposed ports to host"
echo ""

# Load environment
if [ -f "/home/administrator/secrets/litellm.env" ]; then
    source /home/administrator/secrets/litellm.env
fi

if [ -f "/home/administrator/secrets/n8n-mcp.env" ]; then
    source /home/administrator/secrets/n8n-mcp.env
fi

# Use explicit container name to avoid conflicts
CONTAINER_NAME="mcp-proxy-sse"

# Create litellm network if it doesn't exist
echo "Creating litellm-net network..."
docker network create litellm-net 2>/dev/null || echo "Network litellm-net already exists"

# Check if custom image exists, build if needed
if ! docker images | grep -q "mcp-proxy-custom"; then
    echo "Building custom mcp-proxy image with Node.js and Docker..."
    cat > ${SCRIPT_DIR}/Dockerfile << 'EOF'
FROM ghcr.io/sparfenyuk/mcp-proxy:latest

# Install Node.js and Docker CLI for MCP servers
USER root
RUN apk add --no-cache nodejs npm docker-cli bash

# Stay as root for now since we need to run Docker commands
WORKDIR /app
EOF
    docker build -t mcp-proxy-custom:latest ${SCRIPT_DIR}
fi

# Use docker compose for deployment
echo "Deploying MCP proxy with docker compose..."
cd ${SCRIPT_DIR}
docker compose down 2>/dev/null || true
docker compose up -d

# Connect to additional required networks
echo "Connecting to additional networks..."
docker network connect postgres-net mcp-proxy-sse 2>/dev/null || echo "Already connected to postgres-net"

# Wait for startup
sleep 5

# Check if running
if docker ps | grep -q ${CONTAINER_NAME}; then
    echo "✓ mcp-proxy is running as container: ${CONTAINER_NAME}"
    
    # Show the endpoints
    echo ""
    echo "========================================="
    echo "MCP Proxy deployed successfully!"
    echo "========================================="
    echo ""
    echo "🔒 SECURITY: Dual Access Mode"
    echo "   - Port 8585 exposed for unified-tools MCP adapter"
    echo "   - Also accessible via Docker network 'litellm-net'"
    echo ""
    echo "📡 SSE Endpoints:"
    echo ""
    echo "  External (for unified-tools):"
    echo "    Base URL: http://localhost:8585"
    echo ""
    echo "  Internal (for LiteLLM config):"
    echo ""
    echo "  filesystem: http://mcp-proxy-sse:8080/servers/filesystem/sse"
    echo "  fetch:      http://mcp-proxy-sse:8080/servers/fetch/sse"
    echo "  monitoring: http://mcp-proxy-sse:8080/servers/monitoring/sse"
    echo "  postgres:   http://mcp-proxy-sse:8080/servers/postgres/sse"
    echo "  n8n:        http://mcp-proxy-sse:8080/servers/n8n/sse"
    echo "  playwright: http://mcp-proxy-sse:8080/servers/playwright/sse"
    echo "  timescaledb: http://mcp-proxy-sse:8080/servers/timescaledb/sse"
    echo ""
    echo "⚠️  IMPORTANT: These URLs only work from containers on litellm-net"
    echo ""
    echo "Next steps:"
    echo "1. Deploy LiteLLM with docker-compose (connects to litellm-net)"
    echo "2. Update LiteLLM MCP config to use internal URLs above"
else
    echo "✗ mcp-proxy failed to start"
    docker logs ${CONTAINER_NAME} --tail 20
    exit 1
fi