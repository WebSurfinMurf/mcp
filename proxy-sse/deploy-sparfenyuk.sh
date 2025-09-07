#!/bin/bash
set -e

PROJECT_NAME="mcp-proxy"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Deploying sparfenyuk/mcp-proxy (stdio to SSE bridge)..."

# Load environment for passwords
if [ -f "/home/administrator/secrets/litellm.env" ]; then
    source /home/administrator/secrets/litellm.env
    echo "✓ Environment loaded"
fi

# Load additional MCP-specific secrets
if [ -f "/home/administrator/secrets/n8n-mcp.env" ]; then
    source /home/administrator/secrets/n8n-mcp.env
fi

# Stop existing containers
docker stop ${PROJECT_NAME} 2>/dev/null || true
docker rm ${PROJECT_NAME} 2>/dev/null || true

# Create configuration directory
mkdir -p ${SCRIPT_DIR}/config

# Create proxy configuration for all MCP servers
cat > ${SCRIPT_DIR}/config/mcp-servers.json << 'EOF'
{
  "filesystem": {
    "command": "docker",
    "args": ["run", "--rm", "-i", "-v", "/workspace:/workspace", "-v", "/home/administrator/projects:/projects", "mcp/filesystem"],
    "description": "File system operations"
  },
  "memory": {
    "command": "node",
    "args": ["/home/administrator/projects/mcp/memory-postgres/index.js"],
    "env": {
      "POSTGRES_URL": "postgresql://admin:Pass123qp@host.docker.internal:5432/postgres"
    },
    "description": "Memory storage and retrieval"
  },
  "fetch": {
    "command": "docker",
    "args": ["run", "--rm", "-i", "mcp/fetch"],
    "description": "Web content fetching"
  },
  "monitoring": {
    "command": "node",
    "args": ["/home/administrator/projects/mcp/monitoring/src/index.js"],
    "env": {
      "LOKI_URL": "http://host.docker.internal:3100",
      "NETDATA_URL": "http://host.docker.internal:19999"
    },
    "description": "System monitoring and logs"
  },
  "github": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "description": "GitHub operations"
  },
  "postgres": {
    "command": "docker",
    "args": ["run", "--rm", "-i", "crystaldba/postgres-mcp"],
    "env": {
      "PGHOST": "host.docker.internal",
      "PGPORT": "5432",
      "PGUSER": "admin",
      "PGDATABASE": "postgres"
    },
    "description": "PostgreSQL operations"
  },
  "n8n": {
    "command": "/home/administrator/projects/mcp/n8n/mcp-wrapper.sh",
    "description": "n8n workflow automation"
  },
  "playwright": {
    "command": "node",
    "args": ["/home/administrator/projects/mcp/playwright/dist/index.js"],
    "env": {
      "PLAYWRIGHT_API_URL": "http://host.docker.internal:3000"
    },
    "description": "Browser automation"
  },
  "timescaledb": {
    "command": "node",
    "args": ["/home/administrator/projects/mcp/timescaledb/build/index.js"],
    "env": {
      "PGHOST": "host.docker.internal",
      "PGPORT": "5433",
      "PGUSER": "admin",
      "PGDATABASE": "postgres"
    },
    "description": "TimescaleDB operations"
  }
}
EOF

echo "Starting sparfenyuk/mcp-proxy container..."

# Run the official sparfenyuk/mcp-proxy container
# It needs Node.js to run the MCP servers, so we'll use a custom build
docker run -d \
  --name ${PROJECT_NAME} \
  --restart unless-stopped \
  --network traefik-proxy \
  -p 8585:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /home/administrator/projects:/home/administrator/projects:ro \
  -v /workspace:/workspace \
  -v ${SCRIPT_DIR}/config:/config:ro \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
  -e PGPASSWORD="${POSTGRES_PASSWORD}" \
  -e TIMESCALE_PASSWORD="${TIMESCALE_PASSWORD}" \
  -e N8N_API_KEY="${N8N_API_KEY}" \
  -e N8N_API_URL="http://host.docker.internal:5678" \
  --add-host=host.docker.internal:host-gateway \
  ghcr.io/sparfenyuk/mcp-proxy:latest \
  node /home/administrator/projects/mcp/memory-postgres/index.js \
  --sseEndpoint /sse

# Note: The above won't work as-is because sparfenyuk/mcp-proxy expects 
# a single MCP server command. We need a different approach.

# Let me check if we can run multiple instances or use a wrapper
echo "⚠️  Note: sparfenyuk/mcp-proxy v0.8.0+ supports multiple servers"
echo "Checking documentation for proper multi-server configuration..."

# For now, let's stop and reconfigure
docker stop ${PROJECT_NAME} 2>/dev/null || true
docker rm ${PROJECT_NAME} 2>/dev/null || true

echo ""
echo "Need to verify sparfenyuk/mcp-proxy multi-server configuration format."
echo "Checking latest documentation..."