#!/bin/bash
set -e

PROJECT_NAME="mcp-filesystem"
SERVICE_NAME="filesystem"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "====================================="
echo "Deploying MCP Filesystem Service"
echo "====================================="

# Load environment
if [ -f "$HOME/projects/secrets/${PROJECT_NAME}.env" ]; then
    source $HOME/projects/secrets/${PROJECT_NAME}.env
    echo "✓ Environment loaded from secrets/${PROJECT_NAME}.env"
else
    echo "⚠ No environment file found, using defaults"
fi

# Stop and remove existing container
echo ""
echo "Stopping existing container..."
docker stop ${PROJECT_NAME} 2>/dev/null || echo "Container not running"
docker rm ${PROJECT_NAME} 2>/dev/null || echo "Container not found"

# Navigate to service directory
cd ${SCRIPT_DIR}

# Deploy the service
echo ""
echo "Deploying ${PROJECT_NAME}..."
docker compose up -d --build --force-recreate

# Wait for startup
echo ""
echo "Waiting for service startup..."
sleep 10

# Health check with retry
echo ""
echo "Performing health checks..."
for i in {1..5}; do
    echo "Health check attempt $i/5..."
    if curl -f http://127.0.0.1:9073/health 2>/dev/null; then
        echo "✓ Service health check passed"
        break
    elif [ $i -eq 5 ]; then
        echo "✗ Health check failed after 5 attempts"
        docker logs ${PROJECT_NAME} --tail 20
        exit 1
    fi
    sleep 5
done

# SSE endpoint verification (5s timeout)
echo ""
echo "Verifying SSE endpoint..."
for i in {1..3}; do
    echo "SSE check attempt $i/3..."
    response=$(curl -s -S -i -H "Accept: text/event-stream" --max-time 5 http://127.0.0.1:9073/sse 2>/dev/null || echo "")
    if echo "$response" | grep -q "text/event-stream"; then
        echo "✓ SSE endpoint responding correctly"
        break
    elif [ $i -eq 3 ]; then
        echo "✗ SSE endpoint not responding correctly"
        echo "Response: $response"
        docker logs ${PROJECT_NAME} --tail 20
        exit 1
    fi
    sleep 3
done

# Test file system access
echo ""
echo "Testing filesystem access..."
docker exec ${PROJECT_NAME} ls -la /workspace >/dev/null 2>&1 && echo "✓ Workspace volume mounted correctly" || echo "✗ Workspace volume mount failed"

# Update main MCP documentation
echo ""
echo "Updating documentation..."
cat >> /home/administrator/projects/mcp/CLAUDE.md <<'EOF_DOC'

## ${SERVICE_NAME} MCP Service
- **Status**: ✅ Deployed $(date '+%Y-%m-%d %H:%M')
- **Port**: 9073
- **Endpoint**: http://127.0.0.1:9073/sse
- **Container**: ${PROJECT_NAME}
- **Network**: Standalone (no dependencies)
- **Environment**: $HOME/projects/secrets/${PROJECT_NAME}.env
- **Workspace**: /home/administrator/projects (read-only)
EOF_DOC

echo ""
echo "====================================="
echo "Deployment Complete!"
echo "====================================="
echo ""
echo "Service Details:"
echo "  Container: ${PROJECT_NAME}"
echo "  Port: 127.0.0.1:9073"
echo "  SSE Endpoint: http://127.0.0.1:9073/sse"
echo "  Health: http://127.0.0.1:9073/health"
echo ""
echo "Codex CLI Registration:"
echo "  codex mcp add ${SERVICE_NAME} --type sse --url http://127.0.0.1:9073/sse"
echo ""
echo "Verification Commands:"
echo "  curl -i -H \"Accept: text/event-stream\" http://127.0.0.1:9073/sse"
echo "  docker logs ${PROJECT_NAME}"
echo "  docker exec ${PROJECT_NAME} ls -la /workspace"
echo ""
