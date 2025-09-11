#!/bin/bash
# Test individual MCP SSE service

set -e

SERVICE_NAME=${1:-postgres}
SERVICE_PORT=""

# Set port based on service
case "$SERVICE_NAME" in
    postgres) SERVICE_PORT=8001 ;;
    fetch) SERVICE_PORT=8002 ;;
    filesystem) SERVICE_PORT=8003 ;;
    github) SERVICE_PORT=8004 ;;
    monitoring) SERVICE_PORT=8005 ;;
    *)
        echo "Error: Unknown service '$SERVICE_NAME'"
        echo "Available services: postgres, fetch, filesystem, github, monitoring"
        exit 1
        ;;
esac

echo "Testing mcp-$SERVICE_NAME on port $SERVICE_PORT..."
echo

# Test 1: Health Check
echo "1. Health check..."
if curl -s -f "http://localhost:$SERVICE_PORT/health"; then
    echo "✓ Health check passed"
else
    echo "✗ Health check failed"
    exit 1
fi
echo

# Test 2: Service Info
echo "2. Service info..."
if curl -s -f "http://localhost:$SERVICE_PORT/info" | jq . 2>/dev/null; then
    echo "✓ Service info endpoint working"
else
    echo "✗ Service info endpoint failed"
    exit 1
fi
echo

# Test 3: Tools List
echo "3. Tools list..."
if curl -s -f "http://localhost:$SERVICE_PORT/tools" | jq . 2>/dev/null; then
    echo "✓ Tools list endpoint working"
else
    echo "✗ Tools list endpoint failed"
    exit 1
fi
echo

# Test 4: SSE Stream
echo "4. SSE stream test..."
if timeout 5s curl -s -H "Accept: text/event-stream" "http://localhost:$SERVICE_PORT/sse" | head -5; then
    echo "✓ SSE stream working"
else
    echo "✗ SSE stream failed"
    exit 1
fi
echo

echo "✓ All tests passed for mcp-$SERVICE_NAME"