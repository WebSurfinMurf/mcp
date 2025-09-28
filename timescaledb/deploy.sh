#!/bin/bash
set -e

PROJECT_NAME="mcp-timescaledb"
SERVICE_NAME="timescaledb"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================"
echo "Deploying MCP TimescaleDB Service"
echo "======================================"

# Load environment
if [ -f "/home/administrator/secrets/${PROJECT_NAME}.env" ]; then
    source /home/administrator/secrets/${PROJECT_NAME}.env
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
    if curl -f http://127.0.0.1:48011/health 2>/dev/null; then
        echo "✓ Service health check passed"
        break
    elif [ $i -eq 5 ]; then
        echo "✗ Health check failed after 5 attempts"
        docker logs ${PROJECT_NAME} --tail 20
        exit 1
    fi
    sleep 5
done

# Test database connectivity
echo ""
echo "Testing database connectivity..."
for i in {1..3}; do
    echo "Database connectivity check attempt $i/3..."
    if docker exec ${PROJECT_NAME} pg_isready -h timescaledb -p 5432 -U tsdbadmin 2>/dev/null; then
        echo "✓ Database connectivity verified"
        break
    elif [ $i -eq 3 ]; then
        echo "✗ Database connectivity failed"
        docker logs ${PROJECT_NAME} --tail 20
        exit 1
    fi
    sleep 3
done

# Test MCP protocol
echo ""
echo "Testing MCP protocol..."
echo '{"jsonrpc": "2.0", "method": "tools/list", "id": "test"}' | python3 ${SCRIPT_DIR}/mcp-bridge.py | jq '.result.tools[].name' > /tmp/timescaledb-tools-test.txt
if [ -s /tmp/timescaledb-tools-test.txt ]; then
    echo "✓ MCP tools available:"
    cat /tmp/timescaledb-tools-test.txt | sed 's/"//g' | sed 's/^/  - /'
    rm /tmp/timescaledb-tools-test.txt
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
- **Port**: 48011
- **Endpoint**: http://127.0.0.1:48011/sse
- **Container**: ${PROJECT_NAME}
- **Network**: postgres-net (connects to TimescaleDB)
- **Environment**: /home/administrator/secrets/${PROJECT_NAME}.env
- **Database**: TimescaleDB (tsdbadmin user, read-only)
EOF

echo ""
echo "======================================"
echo "Deployment Complete!"
echo "======================================"
echo ""
echo "Service Details:"
echo "  Container: ${PROJECT_NAME}"
echo "  Port: 127.0.0.1:48011"
echo "  Health: http://127.0.0.1:48011/health"
echo "  Database: TimescaleDB via postgres-net"
echo ""
echo "Codex CLI Registration:"
echo "  codex mcp add ${SERVICE_NAME} python3 ${SCRIPT_DIR}/mcp-bridge.py"
echo ""
echo "Claude Code CLI Registration:"
echo "  claude mcp add ${SERVICE_NAME} http://127.0.0.1:48011/sse --transport sse --scope user"
echo ""
echo "Verification Commands:"
echo "  curl -f http://127.0.0.1:48011/health"
echo "  docker logs ${PROJECT_NAME}"
echo "  docker exec ${PROJECT_NAME} pg_isready -h timescaledb -p 5432 -U tsdbadmin"
echo ""