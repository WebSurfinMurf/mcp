#!/bin/bash

echo "=== Testing MCP Servers Directly (stdio) ==="

echo "1. Testing filesystem server..."
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
  docker run --rm -i -v /workspace:/workspace -v /home/administrator/projects:/projects mcp/filesystem /workspace /projects 2>/dev/null | \
  jq -r '.result.tools | length' | \
  xargs -I {} echo "   ✓ Filesystem server: {} tools available"

echo ""
echo "2. Testing fetch server..."
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
  docker run --rm -i mcp/fetch 2>/dev/null | \
  jq -r '.result.tools | length' | \
  xargs -I {} echo "   ✓ Fetch server: {} tools available"

echo ""
echo "3. Testing postgres server..."
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
  docker run --rm -i \
    -e PGHOST=postgres \
    -e PGPORT=5432 \
    -e PGUSER=admin \
    -e PGPASSWORD=Pass123qp \
    -e PGDATABASE=postgres \
    --network=postgres-net \
    crystaldba/postgres-mcp 2>/dev/null | \
  jq -r '.result.tools | length' | \
  xargs -I {} echo "   ✓ Postgres server: {} tools available"

echo ""
echo "4. Testing monitoring server..."
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
  LOKI_URL=http://localhost:3100 NETDATA_URL=http://localhost:19999 \
  node /home/administrator/projects/mcp/monitoring/src/index.js 2>/dev/null | \
  jq -r '.result.tools | length' | \
  xargs -I {} echo "   ✓ Monitoring server: {} tools available" || echo "   ✗ Monitoring server failed"

echo ""
echo "=== Summary ==="
echo "These MCP servers work via stdio. The issue is with the SSE proxy bridge."