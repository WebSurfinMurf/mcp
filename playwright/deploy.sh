#!/bin/bash
set -e

PROJECT_NAME="mcp-playwright"
SERVICE_NAME="playwright"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "====================================="
echo "Deploying MCP Playwright Service"
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

# Wait for startup (Playwright needs more time)
echo ""
echo "Waiting for service startup (Playwright needs time to initialize)..."
sleep 20

# Health check with retry
echo ""
echo "Performing health checks..."
for i in {1..5}; do
    echo "Health check attempt $i/5..."
    if curl -f http://127.0.0.1:9075/health 2>/dev/null; then
        echo "✓ Service health check passed"
        break
    elif [ $i -eq 5 ]; then
        echo "✗ Health check failed after 5 attempts"
        docker logs ${PROJECT_NAME} --tail 20
        exit 1
    fi
    sleep 5
done

# SSE endpoint verification
echo ""
echo "Verifying SSE endpoint..."
for i in {1..3}; do
    echo "SSE check attempt $i/3..."
    response=$(curl -s -i -H "Accept: text/event-stream" http://127.0.0.1:9075/sse 2>/dev/null || echo "")
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

# Test MCP protocol
echo ""
echo "Testing MCP protocol..."
echo '{"jsonrpc": "2.0", "method": "tools/list", "id": "test"}' | python3 ${SCRIPT_DIR}/mcp-bridge.py | jq '.result.tools[].name' > /tmp/playwright-tools-test.txt
if [ -s /tmp/playwright-tools-test.txt ]; then
    echo "✓ MCP tools available:"
    cat /tmp/playwright-tools-test.txt | sed 's/"//g' | sed 's/^/  - /'
    rm /tmp/playwright-tools-test.txt
else
    echo "✗ MCP protocol test failed"
    exit 1
fi

# Update main MCP documentation
echo ""
echo "Updating documentation..."
cat >> /home/administrator/projects/mcp/CLAUDE.md << EOF

## ${SERVICE_NAME} MCP Service
- **Status**: ✅ Deployed $(date '+%Y-%m-%d %H:%M')
- **Port**: 9075
- **Endpoint**: http://127.0.0.1:9075/sse
- **Container**: ${PROJECT_NAME}
- **Network**: Standalone (no dependencies)
- **Environment**: $HOME/projects/secrets/${PROJECT_NAME}.env
- **Browser**: Chromium (headless)
EOF

echo ""
echo "====================================="
echo "Deployment Complete!"
echo "====================================="
echo ""
echo "Service Details:"
echo "  Container: ${PROJECT_NAME}"
echo "  Port: 127.0.0.1:9075"
echo "  SSE Endpoint: http://127.0.0.1:9075/sse"
echo "  Health: http://127.0.0.1:9075/health"
echo ""
echo "Codex CLI Registration:"
echo "  codex mcp add ${SERVICE_NAME} python3 ${SCRIPT_DIR}/mcp-bridge.py"
echo ""
echo "Claude Code CLI Registration:"
echo "  claude mcp add ${SERVICE_NAME} http://127.0.0.1:9075/sse --transport sse --scope user"
echo ""
echo "Verification Commands:"
echo "  curl -i -H \"Accept: text/event-stream\" http://127.0.0.1:9075/sse"
echo "  docker logs ${PROJECT_NAME}"
echo ""