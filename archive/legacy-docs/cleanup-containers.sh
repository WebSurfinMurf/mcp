#!/bin/bash
# MCP Container Cleanup Script
# Purpose: Clean up duplicate and unnamed MCP containers
# Philosophy: Understand what we're removing and why

set -e

echo "=== MCP Container Cleanup ==="
echo "This script will clean up duplicate and unnamed MCP containers"
echo ""

# Step 1: Document current state
echo "Current MCP-related containers:"
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | grep -E "mcp|MCP" || true
echo ""

# Step 2: Stop proxies to prevent new spawns
echo "Stopping proxy containers to prevent new spawns..."
docker stop mcp-proxy-main 2>/dev/null || echo "  mcp-proxy-main not running"
docker stop mcp-proxy-sse 2>/dev/null || echo "  mcp-proxy-sse not running"
echo ""

# Step 3: Remove unnamed containers (Docker's random names)
echo "Removing unnamed containers..."
for container in nice_gould priceless_napier compassionate_cohen; do
  if docker ps -a --format "{{.Names}}" | grep -q "^${container}$"; then
    echo "  Removing unnamed container: $container"
    docker stop $container 2>/dev/null || true
    docker rm $container 2>/dev/null || true
  fi
done
echo ""

# Step 4: Remove failed Phase 3 containers
echo "Removing failed Phase 3 containers..."
docker rm mcp-proxy-main 2>/dev/null || echo "  mcp-proxy-main already removed"
docker rm mcp-mcp-db-init-1 2>/dev/null || echo "  mcp-mcp-db-init-1 already removed"
echo ""

# Step 5: Check what remains
echo "=== Remaining MCP Containers ==="
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | grep -E "mcp|MCP" || echo "No MCP containers found"
echo ""

echo "=== Cleanup Complete ==="
echo ""
echo "Next steps:"
echo "1. Decide which proxy approach to use (legacy mcp-proxy-sse or fix new one)"
echo "2. Fix environment variable expansion issue"
echo "3. Use explicit container names to prevent duplicates"