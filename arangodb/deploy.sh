#!/bin/bash
set -e

PROJECT_NAME="mcp-arangodb"
SERVICE_NAME="arangodb"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================"
echo "Deploying MCP ArangoDB Service"
echo "======================================"

# Load environment
if [ -f "$HOME/projects/secrets/${PROJECT_NAME}.env" ]; then
    source $HOME/projects/secrets/${PROJECT_NAME}.env
    echo "✓ Environment loaded from secrets/${PROJECT_NAME}.env"
else
    echo "✗ ERROR: Environment file not found at secrets/${PROJECT_NAME}.env"
    exit 1
fi

# Verify required environment variables
if [ -z "$ARANGODB_URL" ] || [ -z "$ARANGODB_USERNAME" ] || [ -z "$ARANGODB_PASSWORD" ]; then
    echo "✗ ERROR: Missing required environment variables (ARANGODB_URL, ARANGODB_USERNAME, ARANGODB_PASSWORD)"
    exit 1
fi

# Verify networks exist
echo ""
echo "Checking Docker networks..."
for network in arangodb-net mcp-net; do
    if ! docker network inspect $network >/dev/null 2>&1; then
        echo "✗ ERROR: Network $network does not exist"
        echo "  Create with: docker network create $network"
        exit 1
    fi
    echo "✓ Network $network exists"
done

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
    if curl -f http://127.0.0.1:48013/health 2>/dev/null; then
        echo "✓ Service health check passed"
        break
    elif [ $i -eq 5 ]; then
        echo "✗ Health check failed after 5 attempts"
        docker logs ${PROJECT_NAME} --tail 20
        exit 1
    fi
    sleep 5
done

# Test ArangoDB connectivity
echo ""
echo "Testing ArangoDB connectivity..."
for i in {1..3}; do
    echo "Database connectivity check attempt $i/3..."
    if docker exec ${PROJECT_NAME} curl -f http://arangodb:8529/_api/version 2>/dev/null; then
        echo "✓ ArangoDB connectivity verified"
        break
    elif [ $i -eq 3 ]; then
        echo "✗ ArangoDB connectivity failed"
        docker logs ${PROJECT_NAME} --tail 20
        exit 1
    fi
    sleep 3
done

# Test SSE endpoint
echo ""
echo "Testing SSE endpoint..."
if timeout 5 curl -s -H "Accept: text/event-stream" http://127.0.0.1:48013/sse | head -1 | grep -q "data:"; then
    echo "✓ SSE endpoint responding"
else
    echo "⚠ SSE endpoint test inconclusive (may be normal for streaming endpoint)"
fi

echo ""
echo "======================================"
echo "Deployment Complete!"
echo "======================================"
echo ""
echo "Service Details:"
echo "  Container: ${PROJECT_NAME}"
echo "  Port: 127.0.0.1:48013"
echo "  Health: http://127.0.0.1:48013/health"
echo "  Database: ArangoDB via arangodb-net"
echo "  Target DB: ai_memory"
echo ""
echo "Claude Code CLI Registration:"
echo "  claude mcp add ${SERVICE_NAME} http://127.0.0.1:48013/sse --transport sse --scope user"
echo ""
echo "MCP Proxy Integration:"
echo "  Add to /home/administrator/projects/mcp/proxy/config.json"
echo "  Then restart MCP proxy: cd /home/administrator/projects/mcp/proxy && docker compose restart"
echo ""
echo "Verification Commands:"
echo "  curl -f http://127.0.0.1:48013/health"
echo "  docker logs ${PROJECT_NAME}"
echo "  docker exec ${PROJECT_NAME} curl -f http://arangodb:8529/_api/version"
echo ""
