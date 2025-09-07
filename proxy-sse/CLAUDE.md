# MCP Proxy - Production SSE Gateway for MCP Services

## Overview
This directory contains the production deployment configuration for the MCP SSE proxy, which serves as the central gateway for all MCP (Model Context Protocol) services. The infrastructure provides a unified HTTP/SSE interface for stdio-based MCP servers.

## Current Status: ✅ Production Ready
- **Main Gateway**: Running on port 8585
- **Services Available**: 7 operational MCP services (100% operational)
- **Architecture**: Single proxy managing multiple stdio subprocesses
- **Container**: mcp-proxy-sse
- **Last Verified**: 2025-09-07 14:38

## Architecture
```
Applications (LiteLLM, Claude Code, etc.)
    ↓ (HTTP/SSE)
MCP Proxy Gateway (port 8585)
    ├── filesystem (Docker container)
    ├── monitoring (Node.js process)
    ├── fetch (Docker container)
    ├── postgres (Docker container)
    ├── n8n (Node.js with wrapper)
    ├── playwright (Node.js process)
    └── timescaledb (Docker container with wrapper)
```

## Deployment

### Production Deployment
```bash
# Stop existing proxy
docker stop mcp-proxy-sse && docker rm mcp-proxy-sse

# Start with production configuration
docker run -d \
  --name mcp-proxy-sse \
  --restart unless-stopped \
  --network traefik-proxy \
  -p 8585:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /workspace:/workspace \
  -v /home/administrator/projects:/home/administrator/projects:ro \
  -v /home/administrator/secrets:/home/administrator/secrets:ro \
  -v /home/administrator/projects/mcp/proxy-sse/servers-production.json:/app/servers.json:ro \
  mcp-proxy-custom:latest \
  --host 0.0.0.0 --port 8080 --named-server-config /app/servers.json

# Connect to additional networks
docker network connect postgres-net mcp-proxy-sse
```

### Container Details
- **Container Name**: mcp-proxy-sse
- **Port**: 8585 (external) → 8080 (internal)
- **Image**: mcp-proxy-custom:latest (enhanced with Node.js and Docker CLI)
- **Networks**: traefik-proxy, postgres-net

### Key Configuration
The proxy MUST be started with `--host 0.0.0.0` to bind to all interfaces, otherwise it only binds to 127.0.0.1 inside the container and won't be accessible.

## Configuration Files

### servers-production.json (Current - 7 services)
The main production configuration with all working services:

1. **filesystem** - File operations (11 tools)
   - Docker: mcp/filesystem
   - Mounts: /workspace, /projects

2. **monitoring** - Observability (5 tools)
   - Node.js: Local process
   - Connects to: Loki, Netdata

3. **fetch** - Web content fetching (1 tool)
   - Docker: mcp/fetch
   - Features: Markdown conversion

4. **postgres** - Database operations (6+ tools)
   - Docker: crystaldba/postgres-mcp
   - Uses: DATABASE_URI (hardcoded)

5. **n8n** - Workflow automation (8 tools)
   - Node.js: With bash wrapper
   - Requires: API key from secrets

6. **playwright** - Browser automation (7 tools)
   - Node.js: Local process
   - Connects to: Playwright service port 3000

7. **timescaledb** - Time-series database (10 tools)
   - Docker: mcp-timescaledb:latest
   - Wrapper: mcp-wrapper-fixed.sh
   - Connects to: TimescaleDB on port 5433

### Other Configuration Files
- `servers-working.json` - 4 services (before n8n/playwright)
- `servers-minimal.json` - 2 services (testing)
- `servers-with-n8n.json` - 5 services (intermediate)

## SSE Endpoints

### Production Endpoints (Port 8585)
- Filesystem: `http://localhost:8585/servers/filesystem/sse`
- Monitoring: `http://localhost:8585/servers/monitoring/sse`
- Fetch: `http://localhost:8585/servers/fetch/sse`
- PostgreSQL: `http://localhost:8585/servers/postgres/sse`
- n8n: `http://localhost:8585/servers/n8n/sse`
- Playwright: `http://localhost:8585/servers/playwright/sse`
- TimescaleDB: `http://localhost:8585/servers/timescaledb/sse`

### Internal Docker Access
From other containers: `http://mcp-proxy-sse:8080/servers/{service}/sse`

## Testing

### Test All Services
```bash
# Quick validation of all services
for service in filesystem monitoring fetch postgres n8n playwright timescaledb; do
  echo -n "$service: "
  curl -s http://localhost:8585/servers/$service/sse \
    -H "Accept: text/event-stream" --max-time 3 2>&1 | \
    grep -q "event: endpoint" && echo "✓" || echo "✗"
done
```

### Test Individual Service
```bash
# Test specific service SSE endpoint
curl -s http://localhost:8585/servers/postgres/sse \
  -H "Accept: text/event-stream" --max-time 3
```

### Check Logs
```bash
docker logs mcp-proxy-sse --tail 50
```

## Troubleshooting

### Issue: Connection Reset / Connection Refused
**Solution**: Ensure proxy is started with `--host 0.0.0.0` flag, not default `--host 127.0.0.1`

### Issue: Service Not Working
**Check**:
1. Test service directly (bypass proxy)
2. Check proxy logs for startup errors
3. Verify paths and environment variables
4. Ensure dependencies are available

### Issue: Container Name Conflicts
**Solution**: Always stop and remove existing container before starting new one

## Service-Specific Notes

### PostgreSQL
- Uses hardcoded DATABASE_URI to avoid environment variable expansion issues
- Requires connection to postgres-net network

### n8n
- Uses bash wrapper script to load environment variables
- Requires API key from `/home/administrator/secrets/n8n-mcp.env`

### Playwright
- Connects to external Playwright service on port 3000
- Requires Playwright service to be running

### TimescaleDB
- Uses bash wrapper script to handle Docker stdio communication
- Connects to TimescaleDB on port 5433
- Wrapper script removes --name flag to prevent conflicts

### Monitoring
- Needs access to Loki (port 3100) and Netdata (port 19999)
- Uses local Node.js process

## Known Issues

1. **Memory service** - Excluded due to onnxruntime-node library dependency error
2. **Container spawning** - Proxy creates unnamed containers without `--name` parameter
   - Workaround: Periodically run cleanup script to remove unnamed containers
   - Impact: Accumulation of stopped containers over time

## Implementation Philosophy

Following the Validate-First Philosophy:
1. Started with working foundation (4 services)
2. Fixed PostgreSQL authentication issue first
3. Added services one at a time (n8n, then playwright, then timescaledb)
4. Validated each service before adding the next
5. Documented issues for services that don't work
6. Cleaned up duplicate containers to maintain system hygiene

## Commands

### Restart Proxy
```bash
docker restart mcp-proxy-sse
```

### Stop Proxy
```bash
docker stop mcp-proxy-sse
```

### View Status
```bash
docker ps | grep mcp-proxy-sse
```

### Update Configuration
1. Edit `/home/administrator/projects/mcp/proxy-sse/servers-production.json`
2. Restart proxy: `docker restart mcp-proxy-sse`
3. Test services to ensure they still work

### Clean Up Unnamed Containers
```bash
/home/administrator/projects/mcp/cleanup-containers.sh
```

## Summary
The MCP proxy infrastructure provides a stable SSE gateway for 7 out of 8 planned MCP services (100% of targeted services, memory excluded). The architecture successfully bridges stdio-based MCP servers to HTTP/SSE endpoints, enabling integration with cloud-native applications like LiteLLM.

### Key Achievements
- All 7 targeted services operational via SSE
- PostgreSQL authentication fixed with hardcoded DATABASE_URI
- TimescaleDB integration working with wrapper script fix
- Stable proxy configuration with production-ready endpoints
- Container cleanup strategy in place

---
*Last Updated: 2025-09-07 14:40*
*Status: Production (7/7 services operational, 100%)*