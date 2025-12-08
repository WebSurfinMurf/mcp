#!/bin/bash
# Test MCP Tool Calls
# Tests basic MCP functionality

MCP_PORT="${1:-48012}"
MCP_URL="http://localhost:$MCP_PORT/mcp"

echo "Testing MCP Tools at $MCP_URL"
echo "=============================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }
info() { echo -e "[INFO] $1"; }

# Test 1: Initialize
echo ""
echo "Test 1: MCP Initialize"
INIT_RESPONSE=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}')

if echo "$INIT_RESPONSE" | jq -e '.result.serverInfo' >/dev/null 2>&1; then
    pass "Initialize succeeded"
    info "  Server: $(echo "$INIT_RESPONSE" | jq -r '.result.serverInfo.name')"
else
    fail "Initialize failed"
    info "  Response: $INIT_RESPONSE"
fi

# Test 2: List Tools
echo ""
echo "Test 2: List Tools"
TOOLS_RESPONSE=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"2","method":"tools/list","params":{}}')

if echo "$TOOLS_RESPONSE" | jq -e '.result.tools' >/dev/null 2>&1; then
    TOOL_COUNT=$(echo "$TOOLS_RESPONSE" | jq '.result.tools | length')
    pass "Tools listed: $TOOL_COUNT tools available"
    echo "$TOOLS_RESPONSE" | jq -r '.result.tools[].name' | while read tool; do
        info "  - $tool"
    done
else
    fail "List tools failed"
    info "  Response: $TOOLS_RESPONSE"
fi

# Test 3: Get Account Summary (tests IB connectivity)
echo ""
echo "Test 3: Get Account Summary (IB connectivity test)"
ACCOUNT_RESPONSE=$(curl -s --max-time 15 -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"3","method":"tools/call","params":{"name":"get_account_summary","arguments":{}}}')

if echo "$ACCOUNT_RESPONSE" | jq -e '.result.content[0].text' >/dev/null 2>&1; then
    CONTENT=$(echo "$ACCOUNT_RESPONSE" | jq -r '.result.content[0].text')
    if echo "$CONTENT" | grep -qi "not connected\|cannot connect"; then
        fail "IB not connected"
        info "  Response: $CONTENT"
    else
        pass "Account summary retrieved"
        info "  Preview: $(echo "$CONTENT" | head -c 200)..."
    fi
elif echo "$ACCOUNT_RESPONSE" | jq -e '.error' >/dev/null 2>&1; then
    fail "Error calling get_account_summary"
    info "  Error: $(echo "$ACCOUNT_RESPONSE" | jq -r '.error.message')"
else
    fail "Unexpected response"
    info "  Response: $ACCOUNT_RESPONSE"
fi

# Test 4: Lookup Contract (tests market data)
echo ""
echo "Test 4: Lookup Contract (AAPL)"
CONTRACT_RESPONSE=$(curl -s --max-time 15 -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"4","method":"tools/call","params":{"name":"lookup_contract","arguments":{"symbol":"AAPL"}}}')

if echo "$CONTRACT_RESPONSE" | jq -e '.result.content[0].text' >/dev/null 2>&1; then
    CONTENT=$(echo "$CONTRACT_RESPONSE" | jq -r '.result.content[0].text')
    if echo "$CONTENT" | grep -qi "not connected\|cannot connect"; then
        fail "IB not connected for contract lookup"
    elif echo "$CONTENT" | grep -qi "AAPL\|apple"; then
        pass "Contract lookup succeeded"
        info "  Preview: $(echo "$CONTENT" | head -c 200)..."
    else
        info "Contract lookup returned: $(echo "$CONTENT" | head -c 200)..."
    fi
else
    fail "Contract lookup failed"
    info "  Response: $(echo "$CONTRACT_RESPONSE" | head -c 200)"
fi

echo ""
echo "=============================="
echo "Test Summary"
echo "=============================="

# Health check
echo ""
echo "Current Health Status:"
curl -s "http://localhost:$MCP_PORT/health" | jq '{status, ib_connected, circuit_breaker: .circuit_breaker.state, workers_alive: .pool.workers_alive, workers_ib_connected: .pool.workers_ib_connected}'
