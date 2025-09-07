#!/bin/bash
set -e

# Deploy MCP filesystem proxy
SERVER_NAME="filesystem"
PROXY_PORT=8081

echo "🚀 Deploying MCP proxy for ${SERVER_NAME}..."

# Stop existing
docker stop mcp-proxy-${SERVER_NAME} 2>/dev/null || true
docker rm mcp-proxy-${SERVER_NAME} 2>/dev/null || true

# Run the proxy for filesystem MCP
docker run -d \
  --name mcp-proxy-${SERVER_NAME} \
  --restart unless-stopped \
  --network traefik-proxy \
  -p ${PROXY_PORT}:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /workspace:/workspace \
  -v /home/administrator/projects:/projects:ro \
  node:20-alpine \
  sh -c "npm install -g mcp-proxy && mcp-proxy docker run --rm -i -v /workspace:/workspace -v /projects:/projects mcp-filesystem"

echo "✓ MCP proxy for ${SERVER_NAME} running on port ${PROXY_PORT}"
echo "  SSE endpoint: http://localhost:${PROXY_PORT}/sse"