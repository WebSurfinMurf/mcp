# MCP Proxy Integration Plan

## Overview
This document outlines the integration requirements for adding the Keycloak MCP server to the TBXark MCP Proxy.

## Current Proxy Architecture

The MCP Proxy at `localhost:9090` currently serves 10 MCP servers:
- filesystem, postgres, playwright, memory, minio, n8n, timescaledb, ib, arangodb, openmemory

### Configuration Pattern (from config.json)

```json
{
  "mcpProxy": {
    "addr": ":9090",
    "baseURL": "http://localhost:9090",
    "name": "Local MCP Proxy",
    "type": "streamable-http"
  },
  "mcpServers": {
    "service-name": {
      "command": "...",
      "args": [...],
      "env": {...}
    }
  }
}
```

## Keycloak Server Integration

### Option A: Direct Node.js (Recommended)

```json
{
  "keycloak": {
    "command": "node",
    "args": ["/workspace/mcp/keycloak/dist/index.js"],
    "env": {
      "KEYCLOAK_URL": "https://keycloak.ai-servicers.com",
      "KEYCLOAK_REALM": "ai-servicers",
      "KEYCLOAK_ADMIN_USERNAME": "admin",
      "KEYCLOAK_ADMIN_PASSWORD": "..."
    }
  }
}
```

**Pros:**
- Simple, follows existing patterns (postgres, filesystem use npx)
- No additional container needed
- Direct stdio communication

**Cons:**
- Password visible in config.json

### Option B: Wrapper Script (Alternative)

Similar to playwright, minio, openmemory - use a wrapper script that loads secrets:

```bash
#!/bin/bash
# /home/administrator/projects/mcp/proxy/wrappers/keycloak-wrapper.sh
set -a
source /home/administrator/projects/secrets/keycloak-admin.env
set +a
exec node /workspace/mcp/keycloak/dist/index.js
```

```json
{
  "keycloak": {
    "command": "/wrappers/keycloak-wrapper.sh",
    "args": [],
    "env": {}
  }
}
```

**Pros:**
- Secrets not in config.json
- Consistent with other wrapper-based services

**Cons:**
- Requires wrapper script mount

## Security Considerations

### Environment Variable Handling
- **Current State**: Some servers (postgres) have credentials in config.json
- **Recommendation**: Use wrapper script pattern for Keycloak to avoid storing admin password in config

### Network Access
- Keycloak Admin API requires HTTPS to `keycloak.ai-servicers.com`
- MCP proxy container already has external network access
- No additional network configuration needed

### Credential Scope
- Admin credentials have full realm access
- MCP server only exposes 4 specific operations
- Additional rate limiting not required (Keycloak has its own)

## Pre-Integration Checklist

- [ ] Build TypeScript to `dist/` directory
- [ ] Test locally with `npm run dev`
- [ ] Verify all 4 tools work in isolation
- [ ] Create wrapper script (if Option B)
- [ ] Add entry to config.json
- [ ] Restart mcp-proxy container
- [ ] Register with Claude Code CLI
- [ ] Run integration tests

## Endpoint After Integration

```
POST http://localhost:9090/keycloak/mcp
```

### Testing Endpoint
```bash
# List tools
curl -X POST http://localhost:9090/keycloak/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}'

# Create client (example)
curl -X POST http://localhost:9090/keycloak/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc":"2.0",
    "id":"2",
    "method":"tools/call",
    "params":{
      "name":"create_client",
      "arguments":{
        "clientId":"test-client",
        "redirectUris":["http://localhost:8080/*"]
      }
    }
  }'
```

## Related Files
- Proxy Config: `/home/administrator/projects/mcp/proxy/config.json`
- Proxy Compose: `/home/administrator/projects/mcp/proxy/docker-compose.yml`
- Proxy CLAUDE.md: `/home/administrator/projects/mcp/proxy/CLAUDE.md`

---
**Status**: Review Complete
**Recommendation**: Option B (wrapper script) for security
**Last Updated**: 2026-01-25
