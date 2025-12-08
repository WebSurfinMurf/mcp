#!/bin/bash
# Check API Socket Status
# Monitors the IB Gateway API socket and reports status

GATEWAY_CONTAINER="${1:-mcp-ib-gateway-paper}"
EXPECTED_PORT="${2:-4002}"

echo "Checking IB Gateway API Socket"
echo "Container: $GATEWAY_CONTAINER"
echo "Expected Port: $EXPECTED_PORT"
echo "================================"

# Function to get listening ports
get_listening_ports() {
    docker exec "$GATEWAY_CONTAINER" sh -c 'cat /proc/net/tcp' 2>/dev/null | \
        awk 'NR>1 {split($2,a,":"); port=sprintf("%d", "0x"a[2]); if(port >= 4000 && port <= 4010) print port}' | \
        sort -u
}

# Function to check if specific port is listening
is_port_listening() {
    local port=$1
    get_listening_ports | grep -q "^${port}$"
}

# Check jts.ini configuration
echo ""
echo "Configuration (jts.ini):"
JTS_PORT=$(docker exec "$GATEWAY_CONTAINER" grep "LocalServerPort" /home/ibgateway/Jts/jts.ini 2>/dev/null | cut -d'=' -f2)
echo "  LocalServerPort: $JTS_PORT"

# Check environment
echo ""
echo "Environment Variables:"
docker exec "$GATEWAY_CONTAINER" env 2>/dev/null | grep -E 'API_PORT|TWS_API_PORT' | while read line; do
    echo "  $line"
done

# Check socat
echo ""
echo "socat Configuration:"
SOCAT_CMD=$(docker exec "$GATEWAY_CONTAINER" ps aux 2>/dev/null | grep "socat" | grep -v grep | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
if [ -n "$SOCAT_CMD" ]; then
    echo "  Running: $SOCAT_CMD"
else
    echo "  NOT RUNNING"
fi

# Check listening ports
echo ""
echo "Listening Ports (4000-4010):"
PORTS=$(get_listening_ports)
if [ -n "$PORTS" ]; then
    echo "$PORTS" | while read port; do
        if [ "$port" = "$EXPECTED_PORT" ]; then
            echo "  $port ← Expected API port (OK)"
        elif [ "$port" = "4004" ]; then
            echo "  $port ← socat"
        elif [ "$port" = "$JTS_PORT" ]; then
            echo "  $port ← matches jts.ini LocalServerPort"
        else
            echo "  $port"
        fi
    done
else
    echo "  No ports listening in range 4000-4010"
fi

# Main status check
echo ""
echo "================================"
echo "STATUS:"

if is_port_listening "$EXPECTED_PORT"; then
    echo "✓ API socket is listening on port $EXPECTED_PORT"
    echo ""
    echo "The IB Gateway API is ready for connections."
else
    echo "✗ API socket is NOT listening on port $EXPECTED_PORT"
    echo ""
    echo "TROUBLESHOOTING:"
    echo ""

    if [ -n "$JTS_PORT" ] && [ "$JTS_PORT" != "$EXPECTED_PORT" ]; then
        echo "1. Port mismatch detected:"
        echo "   - jts.ini has LocalServerPort=$JTS_PORT"
        echo "   - Expected port is $EXPECTED_PORT"
        echo "   - Either update jts.ini or change expected port"
        echo ""
    fi

    if is_port_listening "4004"; then
        echo "2. socat is running on 4004 but no API backend"
        echo "   - The API socket server needs to be enabled in IB Gateway"
        echo ""
    fi

    echo "3. To enable API socket via VNC:"
    echo "   - Connect to VNC (port 15900)"
    echo "   - Configure → Settings → API → Settings"
    echo "   - Enable 'Enable ActiveX and Socket Clients'"
    echo "   - Set Socket port to $EXPECTED_PORT"
    echo "   - Click Apply"
    echo ""

    echo "4. Alternative: Check if IBC can enable it:"
    echo "   - Add OverrideTwsApiPort=$EXPECTED_PORT to IBC config"
    echo "   - Restart gateway container"
fi

# Monitor mode
if [ "$3" = "--monitor" ]; then
    echo ""
    echo "Starting monitor mode (Ctrl+C to stop)..."
    while true; do
        sleep 5
        if is_port_listening "$EXPECTED_PORT"; then
            echo "[$(date '+%H:%M:%S')] Port $EXPECTED_PORT: LISTENING"
        else
            echo "[$(date '+%H:%M:%S')] Port $EXPECTED_PORT: NOT LISTENING"
        fi
    done
fi
