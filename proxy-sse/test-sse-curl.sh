#!/bin/bash

echo "Testing MCP SSE with curl..."
echo ""

# Get session endpoint for filesystem
echo "1. Getting filesystem SSE endpoint..."
ENDPOINT=$(curl -s -H "Accept: text/event-stream" http://localhost:8585/servers/filesystem/sse --max-time 1 2>&1 | grep "^data:" | head -1 | sed 's/^data: //')
echo "   Endpoint: $ENDPOINT"

# Send tools/list request
echo "2. Sending tools/list request..."
REQUEST='{"jsonrpc":"2.0","method":"tools/list","id":1}'
URL="http://localhost:8585${ENDPOINT}"

# Post and get SSE response
curl -s -X POST "$URL" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d "$REQUEST" \
  --max-time 3 2>&1 | grep -E "^data:" | head -5

echo ""
echo "3. Testing monitoring server..."
ENDPOINT=$(curl -s -H "Accept: text/event-stream" http://localhost:8585/servers/monitoring/sse --max-time 1 2>&1 | grep "^data:" | head -1 | sed 's/^data: //')
echo "   Endpoint: $ENDPOINT"

URL="http://localhost:8585${ENDPOINT}"
curl -s -X POST "$URL" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d "$REQUEST" \
  --max-time 3 2>&1 | grep -E "^data:" | head -5
