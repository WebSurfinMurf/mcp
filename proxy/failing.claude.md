# MCP-Proxy Route Configuration Analysis

## Root Cause Identified

The primary issue is a **route mismatch** between the expected URL pattern and the actual proxy configuration. The failing tests are using the incorrect route pattern.

## Key Findings

### 1. Correct Route Pattern
- **Logs show**: Proxy handles requests at `/postgres/` (note: no `/servers/` prefix)
- **Failed attempts used**: `/servers/postgres/sse` (incorrect)
- **Working route is**: `/postgres/sse` (confirmed by logs and successful test)

### 2. Authentication Working Correctly
- Route `/postgres/sse` returns `401 Unauthorized` without auth token
- Same route works with `Authorization: Bearer changeme-token` (returns SSE stream)
- This confirms auth mechanism is functional

### 3. Configuration Issues in `config.json`
```json
{
  "mcpProxy": {
    "baseURL": "http://localhost:9090",  // Should be linuxserver.lan per CLAUDE.md
    "authTokens": ["${MCP_PROXY_TOKEN}"]  // Literal string, not interpolated
  }
}
```

## Recommended Fixes

### 1. Fix Route Documentation (Immediate)
Update any client configurations and documentation to use:
- ✅ Correct: `http://localhost:9090/postgres/sse`
- ❌ Incorrect: `http://localhost:9090/servers/postgres/sse`

### 2. Fix Configuration Rendering
The current `config.json` contains `"${MCP_PROXY_TOKEN}"` as a literal string rather than the actual token value. The `render-config.sh` script should be run to properly inject the token:

```bash
cd /home/administrator/projects/mcp/proxy
./render-config.sh  # This will fail - no secrets file exists
```

### 3. Create Missing Secrets File
```bash
# Create the expected secrets file
sudo mkdir -p /home/administrator/secrets
echo "MCP_PROXY_TOKEN=changeme-token" | sudo tee /home/administrator/secrets/mcp-proxy.env
sudo chmod 600 /home/administrator/secrets/mcp-proxy.env
```

### 4. Align BaseURL with Documentation
The `config.template.json` uses `linuxserver.lan:9090` but `config.json` uses `localhost:9090`. This should be consistent.

## Container Image Discrepancy
- Expected: `ghcr.io/tbxark/mcp-proxy:v0.39.1`
- Running: `mcp-proxy-custom` (locally built)

This suggests either:
- A custom build was created to address routing issues
- The official image has routing problems

## Status
- ✅ Proxy is functional and properly connected to upstream
- ✅ Authentication mechanism works
- ❌ Route documentation/client configuration is incorrect
- ❌ Token configuration not properly rendered
- ⚠️  Using custom image instead of official release

The failing tests were using the wrong URL pattern. Once corrected to `/postgres/sse` with proper authentication, the proxy works as expected.