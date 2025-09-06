#!/bin/bash
set -e

PROJECT_NAME="mcp-n8n"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "====================================="
echo "MCP n8n Server Deployment"
echo "====================================="

# Stop existing container if running
echo "Stopping existing container (if any)..."
docker stop ${PROJECT_NAME} 2>/dev/null || true
docker rm ${PROJECT_NAME} 2>/dev/null || true

# Build the container
echo "Building Docker image..."
cat > ${SCRIPT_DIR}/Dockerfile << 'EOF'
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY src/ ./src/

# Make executable
RUN chmod +x src/index.js

# Run as node user
USER node

CMD ["node", "src/index.js"]
EOF

docker build -t ${PROJECT_NAME}:latest ${SCRIPT_DIR}

# Deploy container
echo "Deploying MCP n8n server..."
docker run -d \
  --name ${PROJECT_NAME} \
  --restart unless-stopped \
  --network traefik-proxy \
  -e N8N_URL=http://n8n:5678 \
  -e NODE_ENV=production \
  --label "service=mcp" \
  --label "mcp.type=n8n" \
  ${PROJECT_NAME}:latest

# Connect to required networks
echo "Connecting to Docker networks..."
docker network connect traefik-proxy ${PROJECT_NAME} 2>/dev/null || true

# Wait for startup
sleep 3

# Verify deployment
echo ""
echo "Verifying deployment..."
if docker ps | grep -q ${PROJECT_NAME}; then
  echo "✅ MCP n8n server is running"
else
  echo "❌ MCP n8n server failed to start"
  docker logs ${PROJECT_NAME} --tail 20
  exit 1
fi

echo ""
echo "====================================="
echo "Deployment Complete!"
echo "====================================="
echo ""
echo "Container: ${PROJECT_NAME}"
echo "Status: Running"
echo "Network: traefik-proxy"
echo ""
echo "Next steps:"
echo "1. Update Claude Code configuration (~/.config/claude/mcp_servers.json)"
echo "2. Restart Claude Code to load the new MCP server"
echo "3. Test with: list_workflows, get_executions, etc."
echo ""
echo "To view logs:"
echo "  docker logs ${PROJECT_NAME} -f"