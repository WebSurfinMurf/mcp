#!/bin/bash
# Start PostgreSQL v2 in SSE mode for testing

cd /home/administrator/projects/mcp/unified-registry-v2

echo "Starting PostgreSQL v2 in SSE mode on port 8001..."
export DATABASE_URL="postgresql://admin:Pass123qp@localhost:5432/postgres"

# Run in background
./deploy.sh run postgres sse &

sleep 3

echo ""
echo "Testing endpoints:"
echo "================="

# Test health endpoint
echo -n "Health check: "
curl -s http://localhost:8001/health | jq -c .

# Test tools endpoint
echo -n "Tools available: "
curl -s http://localhost:8001/tools | jq -r '.tools[].name' | tr '\n' ' '
echo ""

echo ""
echo "SSE endpoint: http://localhost:8001/sse"
echo "RPC endpoint: http://localhost:8001/rpc"
echo ""
echo "To stop: kill $(ps aux | grep 'mcp_postgres.py' | grep -v grep | awk '{print $2}')"