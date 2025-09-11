#!/bin/bash
# Health check all MCP SSE services

set -e

echo "MCP SSE Services Health Check"
echo "============================="
echo

services=(
    "postgres:8001"
    "fetch:8002"
    "filesystem:8003"
    "github:8004"
    "monitoring:8005"
)

all_healthy=true

for service_info in "${services[@]}"; do
    IFS=':' read -r service port <<< "$service_info"
    container_name="mcp-$service"
    
    echo -n "Checking $container_name... "
    
    # Check if container is running
    if ! docker ps --format "{{.Names}}" | grep -q "^$container_name$"; then
        echo "✗ Container not running"
        all_healthy=false
        continue
    fi
    
    # Check health endpoint
    if curl -s -f --max-time 5 "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "✓ Healthy"
    else
        echo "✗ Health check failed"
        all_healthy=false
    fi
done

echo
if [ "$all_healthy" = true ]; then
    echo "✓ All services are healthy"
    exit 0
else
    echo "✗ Some services are unhealthy"
    exit 1
fi