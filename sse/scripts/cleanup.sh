#!/bin/bash
# Cleanup MCP SSE containers and resources

set -e

echo "MCP SSE Cleanup Script"
echo "====================="
echo

# Stop all MCP SSE containers
echo "Stopping MCP SSE containers..."
docker-compose down 2>/dev/null || true

# Remove any orphaned containers
echo "Removing any orphaned MCP containers..."
for container in mcp-postgres mcp-fetch mcp-filesystem mcp-github mcp-monitoring; do
    if docker ps -a --format "{{.Names}}" | grep -q "^$container$"; then
        echo "Removing $container..."
        docker stop "$container" 2>/dev/null || true
        docker rm "$container" 2>/dev/null || true
    fi
done

# Clean up unused Docker resources
echo "Cleaning up unused Docker resources..."
docker system prune -f

echo "✓ Cleanup complete"