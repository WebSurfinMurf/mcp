#!/bin/bash
# IB Gateway Paper Trading Diagnostic Script
# Run this to check the health of the IB infrastructure

set -e

GATEWAY_CONTAINER="mcp-ib-gateway-paper"
MCP_CONTAINER="mcp-ib-paper"
MCP_PORT="48012"

echo "=============================================="
echo "IB Gateway Paper Trading Diagnostics"
echo "Date: $(date)"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
info() { echo -e "[INFO] $1"; }

echo ""
echo "=== 1. Container Status ==="

# Check gateway container
if docker ps --filter "name=$GATEWAY_CONTAINER" --format "{{.Status}}" | grep -q "Up"; then
    pass "Gateway container ($GATEWAY_CONTAINER) is running"
    GATEWAY_STATUS=$(docker ps --filter "name=$GATEWAY_CONTAINER" --format "{{.Status}}")
    info "  Status: $GATEWAY_STATUS"
else
    fail "Gateway container ($GATEWAY_CONTAINER) is NOT running"
fi

# Check MCP container
if docker ps --filter "name=$MCP_CONTAINER" --format "{{.Status}}" | grep -q "Up"; then
    pass "MCP container ($MCP_CONTAINER) is running"
else
    fail "MCP container ($MCP_CONTAINER) is NOT running"
fi

echo ""
echo "=== 2. Port Analysis (inside gateway) ==="

# Check listening ports inside gateway container
echo "Checking ports 4000-4010 inside gateway container..."
LISTENING_PORTS=$(docker exec $GATEWAY_CONTAINER sh -c 'cat /proc/net/tcp' 2>/dev/null | \
    awk 'NR>1 {split($2,a,":"); port=sprintf("%d", "0x"a[2]); if(port >= 4000 && port <= 4010) print port}' | sort -u)

if echo "$LISTENING_PORTS" | grep -q "4004"; then
    pass "Port 4004 (socat) is listening"
else
    fail "Port 4004 (socat) is NOT listening"
fi

if echo "$LISTENING_PORTS" | grep -q "4002"; then
    pass "Port 4002 (IB Gateway API) is listening"
else
    fail "Port 4002 (IB Gateway API) is NOT listening - THIS IS THE MAIN ISSUE"
fi

if echo "$LISTENING_PORTS" | grep -q "4000"; then
    warn "Port 4000 is listening (jts.ini port)"
fi

info "All listening ports (4000-4010): $(echo $LISTENING_PORTS | tr '\n' ' ')"

echo ""
echo "=== 3. socat Configuration ==="

SOCAT_CMD=$(docker exec $GATEWAY_CONTAINER ps aux 2>/dev/null | grep socat | grep -v grep || echo "NOT FOUND")
if [ "$SOCAT_CMD" != "NOT FOUND" ]; then
    pass "socat is running"
    info "  Command: $(echo $SOCAT_CMD | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')"

    # Check if socat forwards to correct port
    if echo "$SOCAT_CMD" | grep -q "4002"; then
        pass "socat forwards to port 4002"
    elif echo "$SOCAT_CMD" | grep -q "4000"; then
        warn "socat forwards to port 4000 (check if this matches jts.ini)"
    fi
else
    fail "socat is NOT running"
fi

echo ""
echo "=== 4. Configuration Files ==="

# Check jts.ini
JTS_INI=$(docker exec $GATEWAY_CONTAINER cat /home/ibgateway/Jts/jts.ini 2>/dev/null)
if [ -n "$JTS_INI" ]; then
    pass "jts.ini exists"
    LOCAL_PORT=$(echo "$JTS_INI" | grep "LocalServerPort" | cut -d'=' -f2)
    API_ONLY=$(echo "$JTS_INI" | grep "ApiOnly" | cut -d'=' -f2)
    TRUSTED_IPS=$(echo "$JTS_INI" | grep "TrustedIPs" | cut -d'=' -f2)

    info "  LocalServerPort=$LOCAL_PORT"
    info "  ApiOnly=$API_ONLY"
    info "  TrustedIPs=$TRUSTED_IPS"

    if [ "$API_ONLY" = "true" ]; then
        pass "ApiOnly=true (gateway mode)"
    else
        warn "ApiOnly is not true"
    fi
else
    fail "Cannot read jts.ini"
fi

# Check environment variables
echo ""
info "Environment variables:"
docker exec $GATEWAY_CONTAINER env 2>/dev/null | grep -E 'API_PORT|TWS_API_PORT|SOCAT_PORT' | while read line; do
    info "  $line"
done

echo ""
echo "=== 5. IB Gateway Login Status ==="

# Check login status from logs
LOGS=$(docker logs $GATEWAY_CONTAINER --tail 100 2>&1)

if echo "$LOGS" | grep -q "Login has completed"; then
    pass "IB Gateway login completed"
else
    fail "IB Gateway login NOT completed"
fi

if echo "$LOGS" | grep -q "Configuration tasks completed"; then
    pass "IBC configuration tasks completed"
else
    warn "IBC configuration tasks may not be complete"
fi

# Check for errors
ERRORS=$(echo "$LOGS" | grep -iE "error|exception|failed" | tail -5)
if [ -n "$ERRORS" ]; then
    warn "Recent errors in logs:"
    echo "$ERRORS" | while read line; do
        info "  $line"
    done
fi

echo ""
echo "=== 6. MCP Server Health ==="

HEALTH=$(curl -s http://localhost:$MCP_PORT/health 2>/dev/null)
if [ -n "$HEALTH" ]; then
    STATUS=$(echo "$HEALTH" | jq -r '.status' 2>/dev/null)
    IB_CONNECTED=$(echo "$HEALTH" | jq -r '.ib_connected' 2>/dev/null)
    CB_STATE=$(echo "$HEALTH" | jq -r '.circuit_breaker.state' 2>/dev/null)
    WORKERS_ALIVE=$(echo "$HEALTH" | jq -r '.pool.workers_alive' 2>/dev/null)
    WORKERS_IB=$(echo "$HEALTH" | jq -r '.pool.workers_ib_connected' 2>/dev/null)

    if [ "$STATUS" = "healthy" ]; then
        pass "MCP status: $STATUS"
    else
        fail "MCP status: $STATUS"
    fi

    if [ "$IB_CONNECTED" = "true" ]; then
        pass "IB connected: $IB_CONNECTED"
    else
        fail "IB connected: $IB_CONNECTED"
    fi

    info "  Circuit breaker: $CB_STATE"
    info "  Workers alive: $WORKERS_ALIVE"
    info "  Workers IB connected: $WORKERS_IB"
else
    fail "Cannot reach MCP health endpoint"
fi

echo ""
echo "=== 7. Gateway Status (via MCP) ==="

GW_STATUS=$(curl -s http://localhost:$MCP_PORT/gateway/status 2>/dev/null)
if [ -n "$GW_STATUS" ]; then
    GW_STATE=$(echo "$GW_STATUS" | jq -r '.status' 2>/dev/null)
    API_PORT_OPEN=$(echo "$GW_STATUS" | jq -r '.api_port_open' 2>/dev/null)

    info "Gateway status: $GW_STATE"

    if [ "$API_PORT_OPEN" = "true" ]; then
        pass "API port is open (socat reachable)"
    else
        fail "API port is NOT open"
    fi
else
    warn "Cannot reach gateway status endpoint"
fi

echo ""
echo "=== 8. Network Connectivity ==="

# Test connection from MCP container to gateway
docker exec $MCP_CONTAINER sh -c "nc -zv ibgateway-paper 4004 2>&1" && \
    pass "MCP can reach gateway on port 4004" || \
    fail "MCP cannot reach gateway on port 4004"

echo ""
echo "=============================================="
echo "SUMMARY"
echo "=============================================="

# Main issue check
if ! echo "$LISTENING_PORTS" | grep -q "4002"; then
    echo ""
    fail "MAIN ISSUE: IB Gateway API socket (port 4002) is NOT listening"
    echo ""
    echo "Possible causes:"
    echo "  1. API socket not enabled in IB Gateway settings"
    echo "  2. Need to click 'Apply' in API Settings via VNC"
    echo "  3. Port mismatch between jts.ini ($LOCAL_PORT) and expected (4002)"
    echo ""
    echo "To fix via VNC (linuxserver.lan:15900):"
    echo "  1. Configure → Settings → API → Settings"
    echo "  2. Ensure 'Enable ActiveX and Socket Clients' is checked"
    echo "  3. Set Socket port to match your config"
    echo "  4. Click Apply, then OK"
fi

echo ""
echo "Diagnostics complete."
