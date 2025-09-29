# HTTP 404 Error Analysis: TBXark MCP Proxy

**Date**: 2025-01-28
**Issue**: All endpoints return 404 when running filesystem-proxy-deploy.sh
**Proxy**: ghcr.io/tbxark/mcp-proxy:latest

## 🔍 Root Cause Analysis

Based on the test logs and container behavior, I've identified the core issue:

### **Primary Issue: Incorrect Test Script Endpoints**

The testing script was using incorrect endpoints for TBXark proxy:

1. **Correct endpoint**: `/filesystem/mcp` for Streamable HTTP transport
2. **Testing script tried**: `/`, `/filesystem/mcp`, `/mcp` (mixed correct and incorrect)
3. **Actual behavior**: `/filesystem/mcp` should work with POST requests, but script was using GET requests

### **Container Analysis**
- ✅ **Proxy is starting correctly**: "sse server listening on :9190"
- ✅ **Filesystem service connecting**: "Successfully initialized MCP client"
- ✅ **Tools discovered**: "Successfully listed 14 tools"
- ❌ **Wrong endpoints being tested**: All tested paths return 404

## 🔧 Solution

### **Correct TBXark Proxy Endpoints**

Based on the actual proxy behavior and configuration, the correct endpoints are:

1. **Streamable HTTP Endpoints (Per Service)**:
   ```bash
   # Service-specific HTTP endpoints for JSON-RPC
   POST http://localhost:9190/filesystem/mcp
   POST http://localhost:9190/postgres/mcp
   POST http://localhost:9190/fetch/mcp
   ```

2. **No Authentication Required**:
   ```bash
   # Current setup has no authentication layer
   # Standard JSON-RPC Content-Type header sufficient
   Content-Type: application/json
   ```

### **Updated Test Commands**

Replace the current test script content with:

```bash
# 1. Test correct Streamable HTTP endpoint
echo "Testing Streamable HTTP endpoint:"
curl -sS -X POST http://localhost:9190/filesystem/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# 2. Test initialization
echo "Testing JSON-RPC initialization:"
curl -sS -X POST http://localhost:9190/filesystem/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"init","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{}}}'

# 3. Test specific filesystem tool
echo "Testing filesystem tool invocation:"
curl -sS -X POST http://localhost:9190/filesystem/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"list","method":"tools/call","params":{"name":"list_directory","arguments":{"path":"/workspace"}}}'
```

## ✅ Plan Documentation Alignment

### **Plan Documentation Accuracy**

The `planhttp.md` document is actually correct about TBXark behavior:

1. **Correct endpoint pattern**:
   ```
   Plan states: Per-service endpoints
   Reality: TBXark uses `/filesystem/mcp`, `/postgres/mcp` etc.
   ```

2. **Correct transport type**:
   ```
   Plan states: "Streamable HTTP transport"
   Reality: TBXark does provide JSON-RPC over HTTP at POST endpoints
   ```

3. **Authentication correctly omitted**:
   ```
   Plan setup: No authentication layer configured
   Reality: No Bearer token required in current configuration
   ```

## 🔧 Immediate Fix for Testing Script

### **Updated filesystem-proxy-deploy.sh**

```bash
#!/bin/bash
set -euo pipefail

WORKDIR="/home/administrator/projects"
PROXY_DIR="$WORKDIR/mcp/proxy"
LOG_DIR="$WORKDIR/mcp/logs"
LOG_FILE="$LOG_DIR/filesystem-proxy-$(date +%Y%m%d-%H%M%S).log"

mkdir -p "$LOG_DIR"

{
  echo "=== Filesystem Proxy Deployment ==="
  date
  echo

  echo "--- Ensure network exists ---"
  docker network create mcp-http-net 2>/dev/null || true

  echo "--- Start proxy container ---"
  docker rm -f mcp-proxy-test 2>/dev/null || true
  docker run -d --name mcp-proxy-test \
    --network mcp-http-net \
    -p 9190:9190 \
    -v "$WORKDIR:/workspace" \
    -v "$PROXY_DIR/config.json:/config.json" \
    ghcr.io/tbxark/mcp-proxy:latest --config /config.json

  echo "--- Wait for startup ---"
  sleep 3

  echo "--- Inspect proxy logs ---"
  docker logs --tail 20 mcp-proxy-test || true

  echo "--- Test CORRECT Streamable HTTP endpoints ---"
  echo "POST /filesystem/mcp (tools/list) =>"
  curl -sS -X POST http://localhost:9190/filesystem/mcp \
    -H 'Content-Type: application/json' \
    -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' || true

  echo
  echo "POST /filesystem/mcp (initialize) =>"
  curl -sS -X POST http://localhost:9190/filesystem/mcp \
    -H 'Content-Type: application/json' \
    -d '{"jsonrpc":"2.0","id":"init","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{}}}' || true

  echo
  echo "=== End probe ==="
} | tee "$LOG_FILE"

echo "Log saved to $LOG_FILE"
```

## 📋 Plan Corrections Required

### **planhttp.md needs major updates**:

1. **Endpoint correction**:
   ```diff
   - POST /mcp (aggregate HTTP endpoint)
   + GET /service/sse (per-service SSE endpoints)
   ```

2. **Transport clarification**:
   ```diff
   - "Streamable HTTP transport"
   + "SSE transport with JSON-RPC over SSE"
   ```

3. **Authentication documentation**:
   ```diff
   + Add: Bearer token authentication requirement
   + Add: Reference to secrets/mcp-proxy.env
   ```

4. **Configuration alignment**:
   ```diff
   - Use npx @modelcontextprotocol/server-filesystem
   + Match existing proxy/CLAUDE.md configuration
   ```

## 🎯 Testing Strategy

### **Correct Validation Approach**

1. **SSE Connection Test**:
   ```bash
   curl -N -H 'Accept: text/event-stream' \
     -H "Authorization: Bearer $TOKEN" \
     http://localhost:9190/filesystem/sse
   ```

2. **Tool Discovery via SSE**:
   ```bash
   # SSE typically sends tool list on connection
   # Monitor initial SSE events for capability discovery
   ```

3. **Client Integration Test**:
   ```bash
   # Update Claude Code config with correct endpoints
   {
     "mcpServers": {
       "filesystem": {
         "type": "sse",
         "url": "http://localhost:9190/filesystem/sse",
         "headers": {
           "Authorization": "Bearer <token>"
         }
       }
     }
   }
   ```

## 🚀 Resolution Steps

### **Immediate Actions**

1. **Fix the test script** with correct SSE endpoints and authentication
2. **Update planhttp.md** to reflect actual TBXark proxy behavior
3. **Verify token generation** in `/home/administrator/secrets/mcp-proxy.env`
4. **Test SSE connection** instead of HTTP endpoints

### **Verification Commands**

```bash
# 1. Ensure token exists
ls -la /home/administrator/secrets/mcp-proxy.env

# 2. Run corrected test
cd /home/administrator/projects/mcp/testing
./filesystem-proxy-deploy.sh

# 3. Verify SSE stream
export TOKEN=$(grep MCP_PROXY_TOKEN /home/administrator/secrets/mcp-proxy.env | cut -d= -f2)
curl -N -H "Authorization: Bearer $TOKEN" \
  -H 'Accept: text/event-stream' \
  http://localhost:9190/filesystem/sse | head -10
```

## 📊 Summary

**Root Cause**: Testing script uses incorrect endpoints (`/mcp`) instead of actual TBXark endpoints (`/service/sse`)
**Authentication**: Missing required Bearer token from secrets file
**Transport Type**: TBXark uses SSE, not HTTP transport as assumed in plan
**Fix Complexity**: Low - update test script and plan documentation
**Impact**: Testing can proceed once endpoints and auth are corrected

The proxy is actually working correctly - we were just testing the wrong endpoints without authentication.