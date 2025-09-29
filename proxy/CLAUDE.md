# TBXark MCP Proxy - Streamable HTTP Gateway

## 📋 Project Overview
Central MCP proxy using TBXark/mcp-proxy to serve multiple MCP services via Streamable HTTP. Provides a unified HTTP endpoint for Claude Code to access filesystem and database operations.

## 🟢 Current State (2025-09-29)
- **Status**: ✅ Operational with 4 services (filesystem, postgres, memory, puppeteer)
- **Proxy Image**: `ghcr.io/tbxark/mcp-proxy:latest`
- **Listen Address**: `http://localhost:9090`
- **Transport**: Streamable HTTP
- **Services**: filesystem (9 tools), postgres (1 tool + 21 resources), memory (9 tools), puppeteer (7 tools + 1 resource)
- **Total Tools**: 26+ tools available

## 📝 Recent Work & Changes

### Session: 2025-09-29 - Initial Deployment Complete
- **Fixed**: Package version issue - changed `@modelcontextprotocol/server-filesystem` from non-existent `0.2.3` to working `0.6.2`
- **Configured**: Streamable HTTP mode via `"type": "streamable-http"` in proxy config
- **Added**: PostgreSQL MCP service with database connectivity
- **Network**: Added postgres-net network for database access
- **Tested**: Both services fully operational and registered with Claude Code CLI

## 🏗️ Architecture

```
Claude Code CLI
        │ (HTTP)
        ▼
TBXark Proxy (localhost:9090)
        ├── /filesystem/mcp → npx @modelcontextprotocol/server-filesystem@0.6.2
        └── /postgres/mcp → npx @modelcontextprotocol/server-postgres@0.6.2
```

### Network Configuration
- **mcp-net**: External network for MCP service communication
- **postgres-net**: External network for PostgreSQL database access
- **Workspace Mount**: `/home/administrator/projects` → `/workspace` (read-only)

## ⚙️ Configuration

### Files
- **Docker Compose**: `/home/administrator/projects/mcp/proxy/docker-compose.yml`
- **Proxy Config**: `/home/administrator/projects/mcp/proxy/config.json`
- **Status Docs**: `/home/administrator/projects/mcp/planhttp.status.md`

### Current config.json Structure
```json
{
  "mcpProxy": {
    "addr": ":9090",
    "baseURL": "http://localhost:9090",
    "name": "Local MCP Proxy",
    "type": "streamable-http",
    "options": {
      "logEnabled": true,
      "panicIfInvalid": false
    }
  },
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem@0.6.2", "/workspace"],
      "env": {"NODE_NO_WARNINGS": "1"}
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres@0.6.2", "postgresql://admin:Pass123qp@postgres:5432/postgres"],
      "env": {"NODE_NO_WARNINGS": "1"}
    }
  }
}
```

## 🌐 Access & Management

### Service Endpoints
- **Filesystem**: `http://localhost:9090/filesystem/mcp`
- **PostgreSQL**: `http://localhost:9090/postgres/mcp`

### Claude Code CLI Registration
```bash
# Register both services
claude mcp add filesystem http://localhost:9090/filesystem/mcp -t http
claude mcp add postgres http://localhost:9090/postgres/mcp -t http

# Verify registration
claude mcp list
```

### Testing Endpoints
```bash
# Test filesystem initialize
curl -X POST http://localhost:9090/filesystem/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# Test postgres query
curl -X POST http://localhost:9090/postgres/mcp \
  -H 'Content-Type: application/json' \
  -H 'Mcp-Session-Id: test' \
  -d '{"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"query","arguments":{"sql":"SELECT version();"}}}'
```

## 🔗 Integration Points

### Filesystem Service
- **Package**: `@modelcontextprotocol/server-filesystem@0.6.2`
- **Workspace**: `/workspace` (read-only access to `/home/administrator/projects`)
- **Tools**: 9 operations (read_file, write_file, list_directory, create_directory, move_file, search_files, get_file_info, read_multiple_files, list_allowed_directories)

### PostgreSQL Service
- **Package**: `@modelcontextprotocol/server-postgres@0.6.2`
- **Database**: `postgresql://admin:Pass123qp@postgres:5432/postgres`
- **Tools**: 1 query tool (read-only SQL execution)
- **Resources**: 14 database schema resources (tables from LiteLLM, monitoring tables, etc.)
- **Network**: Requires postgres-net for database connectivity

## 🛠️ Operations

### Container Management
```bash
# Start proxy
cd /home/administrator/projects/mcp/proxy
docker compose up -d

# Check status
docker ps --filter name=mcp-proxy
docker logs mcp-proxy --tail 50

# Restart services
docker compose restart

# Stop services
docker compose down
```

### Health Checks
```bash
# Proxy health
docker inspect mcp-proxy --format '{{json .State.Health}}'

# Verify services initialized
docker logs mcp-proxy | grep "All clients initialized"

# Check individual service
docker logs mcp-proxy | grep "filesystem\|postgres"
```

### Configuration Changes
```bash
# 1. Edit config.json
vim config.json

# 2. Restart proxy
docker compose restart

# 3. Verify changes
docker logs mcp-proxy --tail 30
```

## 🔧 Troubleshooting

### Common Issues

**404 on all endpoints**:
- **Cause**: Invalid npm package version in config
- **Solution**: Verify package exists with `docker exec mcp-proxy npm view <package> versions`
- **Fix**: Update config.json with correct version and restart

**Proxy starts but no routes registered**:
- **Cause**: Silent npx subprocess failure
- **Solution**: Check logs for connection/initialization errors
- **Fix**: Verify command, args, and environment variables in config

**PostgreSQL connection fails**:
- **Cause**: Container not on postgres-net network
- **Solution**: Add postgres-net to docker-compose networks
- **Fix**: `docker compose down && docker compose up -d`

**Database authentication errors**:
- **Cause**: Incorrect credentials in connection string
- **Solution**: Verify DATABASE_URL format and credentials
- **Fix**: Update args in config.json postgres section

### Diagnostic Commands
```bash
# Check networks
docker network inspect mcp-net
docker network inspect postgres-net

# Test database connectivity
docker exec mcp-proxy test -f /config/config.json && echo "Config OK"

# View full logs
docker logs mcp-proxy

# Test endpoints manually
curl -v http://localhost:9090/filesystem/mcp
curl -v http://localhost:9090/postgres/mcp
```

## 📋 Standards & Best Practices

### Package Version Management
- Always verify npm package versions exist before using
- Use specific versions (e.g., `@0.6.2`) instead of `latest`
- Check available versions: `npm view <package> versions --json`

### Network Configuration
- Use external networks for shared resources (mcp-net, postgres-net)
- Mount sensitive directories read-only where possible
- Isolate services on appropriate networks

### Security Considerations
- Database credentials in config.json (consider environment variables for production)
- Read-only workspace mount prevents filesystem modifications outside allowed operations
- No external authentication currently (add tokens for production use)

## 🔄 Related Services

### Other MCP Services
- **fetch**: SSE service on port 9072 (separate from proxy)
- **postgres (stdio)**: Direct Python bridge (legacy, replaced by proxy)

### Infrastructure
- **PostgreSQL**: Main database server at postgres:5432
- **Docker Networks**: mcp-net (MCP services), postgres-net (database access)

## 📚 Documentation References
- **Planning**: `/home/administrator/projects/mcp/planhttp.md`
- **Status**: `/home/administrator/projects/mcp/planhttp.status.md`
- **Fix History**: `/home/administrator/projects/mcp/fixhttp.status.md`
- **Session Notes**: `/home/administrator/projects/AINotes/lastsession.md`

---

**Last Updated**: 2025-09-29
**Status**: ✅ Operational - 2 services, fully tested
**Next Steps**: Evaluate additional services (fetch, minio, playwright, etc.)