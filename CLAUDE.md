# MCP Infrastructure - Model Context Protocol Services

*Last Updated: 2025-09-08*
*Status: ✅ Fully Operational with Unified Registry*

## Overview
Centralized directory for all MCP (Model Context Protocol) services that provide Claude Code and other tools with programmatic capabilities. Now features a **Unified MCP Registry** that serves as a single source of truth for all MCP tools.

## Architecture

### SSE Proxy Gateway
- **Container**: `mcp-proxy-sse`
- **Port**: 8585
- **Directory**: `/home/administrator/projects/mcp/proxy-sse/`
- **Config**: `servers-production.json`
- **Purpose**: Bridges stdio-based MCP servers to HTTP/SSE endpoints

### Service Structure
```
/home/administrator/projects/mcp/
├── unified-registry/   # ⭐ NEW: Single source of truth for all MCP tools
├── proxy-sse/          # SSE gateway proxy
├── filesystem/         # File operations
├── fetch/             # Web content fetching
├── postgres/          # PostgreSQL operations
├── timescaledb/       # Time-series database
├── monitoring/        # Logs and metrics
├── n8n/              # Workflow automation
├── playwright/        # Browser automation
└── memory-postgres/   # Vector memory (currently broken)
```

## Unified MCP Registry (NEW) ⭐

### Overview
- **Location**: `/home/administrator/projects/mcp/unified-registry/`
- **Purpose**: Central registry for all MCP tool definitions
- **Status**: ✅ Phase 2 Complete - 7 services, 24 tools
- **Benefits**: 
  - Single source of truth for Claude Code and LiteLLM
  - Consistent `service_tool` naming convention
  - No duplication of tool definitions
  - Platform-agnostic adapters

### Integrated Services (24 tools)
1. **filesystem** (4 tools) - File operations
2. **postgres** (2 tools) - Database queries
3. **github** (3 tools) - GitHub API
4. **monitoring** (5 tools) - Logs & metrics
5. **n8n** (3 tools) - Workflow automation
6. **playwright** (4 tools) - Browser automation
7. **timescaledb** (3 tools) - Time-series DB

### Claude Code Integration
```json
// Add to ~/.config/claude/mcp_servers.json
{
  "unified-tools": {
    "command": "/home/administrator/projects/mcp/unified-registry/run_claude_adapter.sh",
    "args": []
  }
}
```

## Naming Standards

### Directory Structure
- Pattern: `/home/administrator/projects/mcp/{service}/`
- Example: `/home/administrator/projects/mcp/postgres/`

### Container Names
- Pattern: `mcp-{service}`
- Examples: `mcp-filesystem`, `mcp-postgres-stdio`, `mcp-proxy-sse`

### Secret Files
- Pattern: `/home/administrator/secrets/mcp-{service}.env`
- Examples: `mcp-postgres.env`, `mcp-timescaledb.env`, `mcp-n8n.env`

### Wrapper Scripts
- Standard name: `mcp-wrapper.sh` in each service directory
- Purpose: Handle container naming, environment loading, and stdio communication

## Working Services (7/7)

### 1. Filesystem
- **Endpoint**: `http://localhost:8585/servers/filesystem/sse`
- **Container**: `mcp-filesystem`
- **Type**: Docker container
- **Tools**: File read/write operations

### 2. Fetch
- **Endpoint**: `http://localhost:8585/servers/fetch/sse`
- **Container**: `mcp-fetch`
- **Type**: Docker container
- **Tools**: Web content fetching

### 3. PostgreSQL
- **Endpoint**: `http://localhost:8585/servers/postgres/sse`
- **Container**: `mcp-postgres-stdio`
- **Type**: Docker container
- **Database**: `postgresql://admin:Pass123qp@postgres:5432/postgres`
- **Tools**: Database operations

### 4. TimescaleDB
- **Endpoint**: `http://localhost:8585/servers/timescaledb/sse`
- **Container**: `mcp-timescaledb`
- **Type**: Docker container
- **Database**: Port 5433
- **Tools**: Time-series operations

### 5. Monitoring
- **Endpoint**: `http://localhost:8585/servers/monitoring/sse`
- **Type**: Node.js process
- **Tools**: Log queries, metrics

### 6. n8n
- **Endpoint**: `http://localhost:8585/servers/n8n/sse`
- **Type**: Node.js with bash wrapper
- **Tools**: Workflow automation

### 7. Playwright
- **Endpoint**: `http://localhost:8585/servers/playwright/sse`
- **Type**: Node.js process
- **Tools**: Browser automation

## Excluded Services

### Memory-Postgres
- **Status**: Broken
- **Issue**: onnxruntime-node library dependency
- **Solution**: Would require containerization

## Testing Services

### Quick Test All Services
```bash
for service in filesystem fetch postgres timescaledb monitoring n8n playwright; do
  echo -n "$service: "
  curl -s -H "Accept: text/event-stream" --max-time 2 \
    "http://localhost:8585/servers/$service/sse" | \
    head -1 | grep -q "event: endpoint" && echo "✓" || echo "✗"
done
```

### Test Individual Service
```bash
curl -s -H "Accept: text/event-stream" \
  "http://localhost:8585/servers/filesystem/sse"
```

## Management Commands

### Restart Proxy
```bash
docker restart mcp-proxy-sse
```

### Check Container Status
```bash
docker ps --format "table {{.Names}}\t{{.Image}}" | grep "^mcp-"
```

### Clean Up Containers
```bash
/home/administrator/projects/mcp/cleanup-containers.sh
```

### View Proxy Logs
```bash
docker logs mcp-proxy-sse --tail 50
```

## Configuration Files

### Main Proxy Configuration
`/home/administrator/projects/mcp/proxy-sse/servers-production.json`
- Defines all service endpoints
- Specifies command and arguments for each service
- Uses wrapper scripts for Docker services

### Environment Files
All secrets stored in `/home/administrator/secrets/`:
- `mcp-postgres.env` - PostgreSQL credentials
- `mcp-timescaledb.env` - TimescaleDB credentials
- `mcp-n8n.env` - n8n API credentials
- `mcp-proxy-sse.env` - Proxy configuration

## Implementation Notes

### Container Naming Strategy
Each Docker-based service uses a wrapper script that:
1. Stops any existing container with the same name
2. Removes the stopped container
3. Starts new container with standardized name

This ensures only one instance runs and names are predictable.

### Environment Variable Handling
- PostgreSQL uses hardcoded DATABASE_URI due to Docker expansion limitations
- Other services load credentials from standardized secret files
- Wrapper scripts handle environment variable loading

### Known Limitations
1. PostgreSQL DATABASE_URI must be hardcoded (Docker env expansion issue)
2. Memory service excluded due to library dependencies
3. Services run on-demand and terminate after use

## Recent Changes (2025-09-07)

### Standardization Complete
- ✅ All directories follow `mcp/{service}` structure
- ✅ All containers use `mcp-{service}` naming
- ✅ All secrets use `mcp-{service}.env` format
- ✅ Proxy directory renamed to `proxy-sse`
- ✅ Fixed TimescaleDB wrapper script naming
- ✅ Removed duplicate secret files

### Container Management
- Implemented standard wrapper scripts
- Fixed unnamed container spawning issue
- Created cleanup script for maintenance

## Troubleshooting

### Service Not Responding
1. Check proxy is running: `docker ps | grep mcp-proxy-sse`
2. Test endpoint directly with curl
3. Check wrapper script permissions
4. Verify secret files exist

### Container Name Conflicts
- Wrapper scripts now handle cleanup automatically
- Run cleanup script if needed: `./cleanup-containers.sh`

### Authentication Issues
- Verify credentials in `/home/administrator/secrets/mcp-{service}.env`
- Check DATABASE_URI in PostgreSQL configuration
- Ensure services can reach their backends

## Future Improvements
- [ ] Fix memory service (containerize or resolve dependencies)
- [ ] Add service health monitoring
- [ ] Implement automatic container cleanup cron
- [ ] Add metrics collection for service usage
- [ ] Create unified deployment script

---
*Infrastructure follows Validate-First Philosophy: Each component tested and validated before integration*