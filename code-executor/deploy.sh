#!/bin/bash
# MCP Code Executor Deployment Script

set -e

# Load secrets
set -a
source "$HOME/projects/secrets/gitlab.env" 2>/dev/null || true
source "$HOME/projects/secrets/code-executor.env" 2>/dev/null || true
set +a

echo "🚀 Deploying MCP Code Executor..."
echo "=================================="
echo ""

# Create data directory
echo "📁 Creating data directory..."
mkdir -p /home/administrator/projects/data/mcp-executor/{servers,skills,examples}
chmod -R 755 /home/administrator/projects/data/mcp-executor

# Build and start container
echo "🔨 Building container..."
docker compose build

echo "▶️  Starting service..."
docker compose up -d

# Wait for health check
echo "⏳ Waiting for service to be healthy..."
sleep 5

# Check health (no API key needed for basic health)
echo "🏥 Checking health..."
if curl -sf http://localhost:9091/health > /dev/null; then
    echo "✅ Service is healthy!"
    curl -s http://localhost:9091/health | python3 -m json.tool
else
    echo "❌ Service failed health check"
    echo "📋 Logs:"
    docker logs mcp-code-executor --tail 20
    exit 1
fi

# Verify RBAC
echo ""
echo "🔐 Verifying RBAC..."
if [ -n "$CODE_EXECUTOR_ADMIN_KEY" ]; then
    ADMIN_SERVERS=$(curl -sf -H "X-API-Key: $CODE_EXECUTOR_ADMIN_KEY" http://localhost:9091/tools | python3 -c "import sys,json; print(json.load(sys.stdin)['servers'])" 2>/dev/null)
    echo "  Admin role: ${ADMIN_SERVERS:-FAILED} servers"
fi
if [ -n "$CODE_EXECUTOR_DEVELOPER_KEY" ]; then
    DEV_SERVERS=$(curl -sf -H "X-API-Key: $CODE_EXECUTOR_DEVELOPER_KEY" http://localhost:9091/tools | python3 -c "import sys,json; print(json.load(sys.stdin)['servers'])" 2>/dev/null)
    echo "  Developer role: ${DEV_SERVERS:-FAILED} servers"
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Service Information:"
echo "  API Endpoint: http://localhost:9091"
echo "  Health Check: http://localhost:9091/health"
echo "  Tools List:   http://localhost:9091/tools (requires API key)"
echo ""
echo "🔧 Next Steps:"
echo "  1. Generate tool wrappers: docker exec mcp-code-executor npm run generate-wrappers"
echo "  2. Restart Claude Code CLI to pick up new MCP config"
echo ""
