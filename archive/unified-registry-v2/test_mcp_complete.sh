#!/bin/bash
# Comprehensive MCP protocol test with logging

set -e

LOG_DIR="logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/test_complete_${TIMESTAMP}.log"

echo "=== MCP Complete Test Started: $(date) ===" | tee "$LOG_FILE"

# Function to log
log() {
    echo "[$(date +%H:%M:%S)] $1" | tee -a "$LOG_FILE"
}

# Test 1: Basic execution test
log "TEST 1: Basic execution test"
if timeout 2 ./deploy.sh run postgres stdio < /dev/null 2>&1 | grep -q "jsonrpc"; then
    log "✓ Service starts and outputs JSON-RPC"
else
    log "✗ Service failed to start properly"
fi

# Test 2: Initialize protocol
log "TEST 2: Initialize protocol"
INIT_RESPONSE=$(echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1}' | timeout 2 ./deploy.sh run postgres stdio 2>/dev/null)
if echo "$INIT_RESPONSE" | grep -q '"protocolVersion"'; then
    log "✓ Initialize response received"
    echo "$INIT_RESPONSE" >> "$LOG_FILE"
else
    log "✗ Initialize failed"
fi

# Test 3: Tools list after initialize
log "TEST 3: Tools list after initialize"
TOOLS_RESPONSE=$(echo -e '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1}\n{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}' | timeout 2 ./deploy.sh run postgres stdio 2>/dev/null | tail -1)
if echo "$TOOLS_RESPONSE" | grep -q '"tools"'; then
    log "✓ Tools list received"
    echo "$TOOLS_RESPONSE" | jq '.result.tools | length' >> "$LOG_FILE" 2>/dev/null || echo "Failed to parse tools" >> "$LOG_FILE"
else
    log "✗ Tools list failed"
fi

# Test 4: Tool call
log "TEST 4: Tool call (list_databases)"
TOOL_RESPONSE=$(echo -e '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1}\n{"jsonrpc":"2.0","method":"tools/call","params":{"name":"list_databases","arguments":{}},"id":2}' | timeout 2 ./deploy.sh run postgres stdio 2>/dev/null | tail -1)
if echo "$TOOL_RESPONSE" | grep -q '"result"'; then
    log "✓ Tool call succeeded"
    echo "$TOOL_RESPONSE" | jq '.result' >> "$LOG_FILE" 2>/dev/null || echo "$TOOL_RESPONSE" >> "$LOG_FILE"
else
    log "✗ Tool call failed"
    echo "$TOOL_RESPONSE" >> "$LOG_FILE"
fi

# Test 5: Multiple rapid calls (buffering test)
log "TEST 5: Multiple rapid calls"
(
    echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1}'
    echo '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}'
    echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"list_databases","arguments":{}},"id":3}'
) | timeout 3 ./deploy.sh run postgres stdio 2>/dev/null > "$LOG_DIR/multi_response_${TIMESTAMP}.json"

RESPONSE_COUNT=$(grep -c "jsonrpc" "$LOG_DIR/multi_response_${TIMESTAMP}.json" || echo 0)
log "Received $RESPONSE_COUNT responses from 3 requests"

# Test 6: Check if service stays alive
log "TEST 6: Service persistence test"
(
    echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1}'
    sleep 1
    echo '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}'
    sleep 1
    echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"execute_sql","arguments":{"query":"SELECT 1"}},"id":3}'
) | timeout 5 ./deploy.sh run postgres stdio 2>/dev/null > "$LOG_DIR/persistence_${TIMESTAMP}.json"

PERSIST_COUNT=$(grep -c "jsonrpc" "$LOG_DIR/persistence_${TIMESTAMP}.json" || echo 0)
log "Service handled $PERSIST_COUNT requests with delays"

# Test 7: Error handling
log "TEST 7: Error handling"
ERROR_RESPONSE=$(echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"invalid_tool","arguments":{}},"id":1}' | timeout 2 ./deploy.sh run postgres stdio 2>/dev/null)
if echo "$ERROR_RESPONSE" | grep -q '"error"'; then
    log "✓ Error handling works"
else
    log "✗ Error handling failed"
fi

echo "=== Test Complete ===" | tee -a "$LOG_FILE"
echo "Log saved to: $LOG_FILE"
echo ""
echo "Summary:"
grep "^\\[" "$LOG_FILE" | grep -E "✓|✗" | tail -10