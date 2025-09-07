#!/bin/bash

echo "Testing MCP SSE with inspector in CLI mode..."
echo ""

# Test filesystem server
echo "Testing filesystem server via SSE:"
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
npx @modelcontextprotocol/inspector --cli --transport sse --server-url http://localhost:8585/servers/filesystem/sse 2>&1 | \
grep -E "tools|error" | head -10

echo ""
echo "Testing monitoring server via SSE:"
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
npx @modelcontextprotocol/inspector --cli --transport sse --server-url http://localhost:8585/servers/monitoring/sse 2>&1 | \
grep -E "tools|error" | head -10