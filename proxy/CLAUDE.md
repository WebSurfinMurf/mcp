# MCP Proxy - SSE Bridge for stdio MCP Servers

## Overview
This directory contains the deployment configuration for sparfenyuk/mcp-proxy, which bridges stdio-based MCP (Model Context Protocol) servers to SSE (Server-Sent Events) endpoints that can be consumed by LiteLLM and other MCP clients.

## Purpose
Many MCP servers only support stdio (standard input/output) transport, but LiteLLM and cloud-native applications work better with HTTP-based transports like SSE. This proxy bridges that gap by:
- Running stdio MCP servers as subprocesses
- Exposing them via SSE/HTTP endpoints
- Managing session state and protocol translation

## Architecture
```
LiteLLM Container
    ↓ (HTTP/SSE)
MCP Proxy (port 8585 external, 8080 internal)
    ├── filesystem (Docker container)
    └── monitoring (Node.js process)
```

## Deployment

### Quick Deploy
```bash
cd /home/administrator/projects/mcp/proxy
./deploy.sh
```

### Container Details
- **Container Name**: `mcp-proxy-sse`
- **Image**: `mcp-proxy-custom:latest` (based on sparfenyuk/mcp-proxy with Node.js and Docker CLI added)
- **External Port**: 8585
- **Internal Port**: 8080
- **Network**: traefik-proxy, postgres-net, loki-net

### Key Configuration
The proxy MUST be started with `--host 0.0.0.0` to bind to all interfaces, otherwise it only binds to 127.0.0.1 inside the container and won't be accessible.

## Configuration Files

### servers.json / servers-minimal.json
Defines the MCP servers to expose. Currently configured servers:

1. **filesystem** - Docker-based file operations
   - Command: `docker run --rm -i -v /workspace:/workspace -v /home/administrator/projects:/projects mcp/filesystem`
   - Provides: File read, write, list, search operations

2. **monitoring** - Node.js observability server  
   - Command: `node /home/administrator/projects/mcp/monitoring/src/index.js`
   - Provides: Loki log queries, Netdata metrics

### servers-full.json (all 9 servers)
Contains configuration for all MCP servers but some have dependency issues:
- memory, fetch, github, postgres, n8n, playwright, timescaledb

## SSE Endpoints

### Internal Docker Access
- Filesystem: `http://mcp-proxy-sse:8080/servers/filesystem/sse`
- Monitoring: `http://mcp-proxy-sse:8080/servers/monitoring/sse`

### External Access (for testing)
- Filesystem: `http://localhost:8585/servers/filesystem/sse`
- Monitoring: `http://localhost:8585/servers/monitoring/sse`

## Testing

### Test SSE Connection
```bash
# Get SSE endpoint
curl -H "Accept: text/event-stream" http://localhost:8585/servers/filesystem/sse

# Test with Python script
python3 /home/administrator/projects/mcp/proxy/test-sse.py

# Test with shell script  
./test-sse-curl.sh
```

### Test Direct stdio (without proxy)
```bash
./test-direct.sh
```

## Troubleshooting

### Issue: Connection Reset / Connection Refused
**Symptom**: `curl: (56) Recv failure: Connection reset by peer`

**Solution**: Ensure proxy is started with `--host 0.0.0.0` flag, not default `--host 127.0.0.1`

### Issue: Wrong Container Name
**Symptom**: Container named "litellm" or "mcp-proxy" instead of "mcp-proxy-sse"

**Solution**: Use explicit `CONTAINER_NAME="mcp-proxy-sse"` variable in deploy.sh

### Issue: SSE Not Initializing
**Symptom**: "Received request before initialization was complete" in logs

**Solution**: This is a known issue with the SSE handshake. The proxy needs proper initialization sequence which some clients don't handle correctly.

### Check Logs
```bash
docker logs mcp-proxy-sse --tail 50
```

### Verify Running
```bash
docker ps | grep mcp-proxy-sse
```

### Test Internal Connectivity
```bash
# From another container
docker exec litellm curl -s http://mcp-proxy-sse:8080/servers/filesystem/sse
```

## Integration with LiteLLM

### LiteLLM config.yaml
```yaml
litellm_settings:
  mcp_servers:
    filesystem:
      transport: "sse"
      url: "http://mcp-proxy-sse:8080/servers/filesystem/sse"
      description: "File system operations"
    
    monitoring:
      transport: "sse"  
      url: "http://mcp-proxy-sse:8080/servers/monitoring/sse"
      description: "System monitoring and logs"
```

### Current Status
- LiteLLM v1.75.8 configuration updated but `/v1/mcp/tools` returns empty
- MCP Gateway feature may require newer version or additional configuration
- SSE endpoints are working and accessible from LiteLLM container

## Known Issues
1. Some MCP servers fail with library dependency errors (memory-postgres needs rebuild)
2. SSE initialization requires proper handshake that not all clients implement
3. LiteLLM MCP Gateway integration still being validated

## Future Improvements
- Add remaining 7 MCP servers once dependencies resolved
- Consider using IBM's mcp-context-forge for more robust gateway
- Implement health checks for each MCP server
- Add authentication/authorization layer

## References
- sparfenyuk/mcp-proxy: https://github.com/sparfenyuk/mcp-proxy
- MCP Specification: https://modelcontextprotocol.io/
- LiteLLM MCP Docs: https://docs.litellm.ai/docs/mcp

---
*Last Updated: 2025-09-07*
*Status: Operational (2 of 9 servers working)*