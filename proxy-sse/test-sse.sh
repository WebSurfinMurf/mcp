#!/bin/bash

# Test MCP SSE connection with proper initialization
echo "Testing MCP SSE endpoints..."

# Test filesystem server
echo "Testing filesystem server..."
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test-client","version":"1.0.0"}},"id":1}' | \
curl -X POST http://localhost:8585/servers/filesystem/sse \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  --data-binary @- \
  --no-buffer \
  --max-time 5 2>&1 | head -20

echo ""
echo "Testing memory server..."
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test-client","version":"1.0.0"}},"id":1}' | \
curl -X POST http://localhost:8585/servers/memory/sse \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  --data-binary @- \
  --no-buffer \
  --max-time 5 2>&1 | head -20