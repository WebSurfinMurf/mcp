#!/bin/bash
# Matrix MCP Server Deployment Script
# Created: 2025-10-19

set -e

PROJECT_DIR="/home/administrator/projects/mcp/matrix"
cd "$PROJECT_DIR"

echo "🔧 Matrix MCP Server Deployment"
echo "================================"

# Check if secrets file exists
if [ ! -f "$HOME/projects/secrets/matrix-mcp.env" ]; then
    echo "❌ Error: $HOME/projects/secrets/matrix-mcp.env not found"
    exit 1
fi

# Pull latest changes if needed
if [ -d "server/.git" ]; then
    echo "📥 Updating repository..."
    cd server && git pull && cd ..
fi

# Build and deploy
echo "🏗️  Building Docker image..."
docker compose build

echo "🚀 Starting Matrix MCP Server..."
docker compose up -d

# Wait for health check
echo "⏳ Waiting for service to be healthy..."
sleep 5

# Check health
if docker inspect mcp-matrix --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
    echo "✅ Matrix MCP Server deployed successfully!"
    echo ""
    echo "📊 Service Information:"
    echo "  Container: mcp-matrix"
    echo "  Port: 127.0.0.1:48013"
    echo "  Health: $(docker inspect mcp-matrix --format='{{.State.Health.Status}}')"
    echo "  Logs: docker logs mcp-matrix"
    echo ""
    echo "🔗 MCP Endpoint: http://localhost:48013/mcp"
    echo "🏥 Health Check: http://localhost:48013/health"
else
    echo "⚠️  Service started but health check pending..."
    echo "Check logs: docker logs mcp-matrix"
fi
