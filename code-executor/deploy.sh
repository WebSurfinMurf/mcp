#!/bin/bash
# MCP Code Executor Deployment Script

set -e

# Load secrets (GitLab token needed for issue creation)
set -a
source "$HOME/projects/secrets/gitlab.env" 2>/dev/null || true
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

# Check health
echo "🏥 Checking health..."
if curl -sf http://localhost:3000/health > /dev/null; then
    echo "✅ Service is healthy!"
    curl -s http://localhost:3000/health | python3 -m json.tool
else
    echo "❌ Service failed health check"
    echo "📋 Logs:"
    docker logs mcp-code-executor --tail 20
    exit 1
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Service Information:"
echo "  API Endpoint: http://localhost:3000"
echo "  Health Check: http://localhost:3000/health"
echo "  Tools List:   http://localhost:3000/tools"
echo ""
echo "🔧 Next Steps:"
echo "  1. Generate tool wrappers: docker exec mcp-code-executor npm run generate-wrappers"
echo "  2. Test execution: curl -X POST http://localhost:3000/execute -H 'Content-Type: application/json' -d '{\"code\":\"console.log('Hello World')\"}'"
echo ""
