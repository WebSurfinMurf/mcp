#!/bin/bash
set -e

PROJECT_NAME="mcp-proxy"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Deploying sparfenyuk/mcp-proxy for all MCP servers..."

# Load environment
if [ -f "/home/administrator/secrets/litellm.env" ]; then
    source /home/administrator/secrets/litellm.env
fi

if [ -f "/home/administrator/secrets/n8n-mcp.env" ]; then
    source /home/administrator/secrets/n8n-mcp.env
fi

# Use explicit container name to avoid conflicts
CONTAINER_NAME="mcp-proxy-sse"

# Stop existing
docker stop ${CONTAINER_NAME} 2>/dev/null || true
docker rm ${CONTAINER_NAME} 2>/dev/null || true

# Substitute environment variables in servers.json
envsubst < ${SCRIPT_DIR}/servers.json > ${SCRIPT_DIR}/servers-resolved.json

# Create custom image with Node.js and Docker for running MCP servers
cat > ${SCRIPT_DIR}/Dockerfile << 'EOF'
FROM ghcr.io/sparfenyuk/mcp-proxy:latest

# Install Node.js and Docker CLI for MCP servers
USER root
RUN apk add --no-cache nodejs npm docker-cli bash

# Stay as root for now since we need to run Docker commands
WORKDIR /app
EOF

echo "Building custom mcp-proxy image with Node.js and Docker..."
docker build -t mcp-proxy-custom:latest ${SCRIPT_DIR}

echo "Starting mcp-proxy container..."
# Use explicit container name to avoid conflicts
CONTAINER_NAME="mcp-proxy-sse"
docker run -d \
  --name ${CONTAINER_NAME} \
  --restart unless-stopped \
  --network traefik-proxy \
  -p 8585:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /home/administrator/projects:/home/administrator/projects:ro \
  -v /workspace:/workspace \
  -v ${SCRIPT_DIR}/servers-resolved.json:/app/servers.json:ro \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
  -e PGPASSWORD="${POSTGRES_PASSWORD}" \
  -e TIMESCALE_PASSWORD="${TIMESCALE_PASSWORD}" \
  -e N8N_API_KEY="${N8N_API_KEY}" \
  --add-host=host.docker.internal:host-gateway \
  mcp-proxy-custom:latest \
  --host 0.0.0.0 \
  --port 8080 \
  --named-server-config /app/servers.json

# Connect to necessary networks
echo "Connecting to required networks..."
docker network connect postgres-net ${CONTAINER_NAME} 2>/dev/null || true
docker network connect loki-net ${CONTAINER_NAME} 2>/dev/null || true

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
    echo "🌐 SSE Endpoints for LiteLLM configuration:"
    echo ""
    echo "  filesystem: http://${CONTAINER_NAME}:8080/servers/filesystem/sse"
    echo "  memory:     http://${CONTAINER_NAME}:8080/servers/memory/sse"
    echo "  fetch:      http://${CONTAINER_NAME}:8080/servers/fetch/sse"
    echo "  monitoring: http://${CONTAINER_NAME}:8080/servers/monitoring/sse"
    echo "  github:     http://${CONTAINER_NAME}:8080/servers/github/sse"
    echo "  postgres:   http://${CONTAINER_NAME}:8080/servers/postgres/sse"
    echo "  n8n:        http://${CONTAINER_NAME}:8080/servers/n8n/sse"
    echo "  playwright: http://${CONTAINER_NAME}:8080/servers/playwright/sse"
    echo "  timescaledb: http://${CONTAINER_NAME}:8080/servers/timescaledb/sse"
    echo ""
    echo "External access: http://localhost:8585"
    echo "Internal Docker: http://${CONTAINER_NAME}:8080"
    echo ""
    echo "Next step: Update LiteLLM config.yaml with these SSE endpoints"
else
    echo "✗ mcp-proxy failed to start"
    docker logs ${CONTAINER_NAME} --tail 20
    exit 1
fi