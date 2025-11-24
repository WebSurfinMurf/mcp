# TBXark MCP Proxy - Streamable HTTP Gateway

## 📋 Project Overview
Central MCP proxy using TBXark/mcp-proxy to serve multiple MCP services via Streamable HTTP. Provides a unified HTTP endpoint for Claude Code to access filesystem and database operations.

## 🟢 Current State (2025-11-23)
- **Status**: ✅ Operational with 10 services
- **Proxy Image**: `ghcr.io/tbxark/mcp-proxy:latest`
- **Listen Address**: `http://localhost:9090`
- **Transport**: Streamable HTTP
- **Services**: filesystem, postgres, playwright, memory, minio, n8n, timescaledb, ib, arangodb, openmemory
- **Total Tools**: 67 tools available across all services

## 📝 Recent Work & Changes

### Session: 2025-11-23 - OpenMemory MCP Integration
- **Added**: OpenMemory MCP server for semantic memory operations
- **Created**: `/wrappers/openmemory-wrapper.sh` - HTTP-to-stdio bridge for mcp-openmemory container
- **Updated**: `config.json` - added "openmemory" server entry
- **Tools**: 4 tools available (add_memory, search_memories, list_memories, delete_memory)
- **Container**: mcp-openmemory:8000/mcp (FastAPI HTTP wrapper for OpenMemory REST API)
- **Backend**: mem0 v1.0.0 with Gemini embeddings (768-dim), Qdrant vector store
- **Verified**: ✅ All tools accessible via http://localhost:9090/openmemory/mcp
- **Integration**: `/cmemory` slash command uses OpenMemory MCP tools
- **Total Services**: 10 servers with 67 tools

### Session: 2025-11-01 - Replaced Puppeteer with Playwright
- **Removed**: Puppeteer MCP (npm package @modelcontextprotocol/server-puppeteer)
- **Added**: Playwright MCP integration via wrapper script
- **Created**: `/wrappers/playwright-wrapper.sh` - HTTP-to-stdio bridge for mcp-playwright container
- **Updated**: `config.json` - replaced "puppeteer" with "playwright" entry
- **Tools**: 6 tools available (navigate_to_page, take_screenshot, extract_text, click_element, fill_form, get_page_info)
- **Container**: mcp-playwright:8000/mcp (Chromium headless, 2GB shm_size)
- **Verified**: ✅ All tools accessible via http://localhost:9090/playwright/mcp
- **Reason**: Using actual deployed Playwright container instead of npm package

### Session: 2025-09-29 - Initial Deployment Complete
- **Fixed**: Package version issue - changed `@modelcontextprotocol/server-filesystem` from non-existent `0.2.3` to working `0.6.2`
- **Configured**: Streamable HTTP mode via `"type": "streamable-http"` in proxy config
- **Added**: PostgreSQL MCP service with database connectivity
- **Network**: Added postgres-net network for database access
- **Tested**: Both services fully operational and registered with Claude Code CLI

## 🏗️ Architecture

```
Claude Code CLI / Open WebUI / Laptop
        │ (HTTP)
        ▼
TBXark Proxy (localhost:9090)
        ├── /filesystem/mcp → npx @modelcontextprotocol/server-filesystem@0.6.2
        ├── /postgres/mcp → npx @modelcontextprotocol/server-postgres@0.6.2
        ├── /playwright/mcp → wrapper → mcp-playwright:8000
        ├── /memory/mcp → npx @modelcontextprotocol/server-memory
        ├── /minio/mcp → wrapper → mcp-minio:9076
        ├── /n8n/mcp → wrapper → n8n:5678
        ├── /timescaledb/mcp → wrapper → mcp-timescaledb:48011
        ├── /ib/mcp → wrapper → mcp-ib:48012
        ├── /arangodb/mcp → npx arango-server (stdio)
        └── /openmemory/mcp → wrapper → mcp-openmemory:8000
```

### MCP Services (10 servers, 67 tools)

**📁 Filesystem** (9 tools) - File operations
- npx @modelcontextprotocol/server-filesystem@0.6.2
- Workspace: `/workspace` (read-only)

**🗄️ PostgreSQL** (1 tool) - Database operations
- npx @modelcontextprotocol/server-postgres@0.6.2
- Connection: postgres:5432/postgres

**🌐 Playwright** (6 tools) - Browser automation
- HTTP wrapper to mcp-playwright:8000
- Headless Chromium for web interactions

**🧠 Memory** (9 tools) - Knowledge graph storage
- npx @modelcontextprotocol/server-memory
- Persistent JSONL storage in mcp-memory-data volume

**🪣 MinIO** (9 tools) - S3-compatible object storage
- HTTP wrapper to mcp-minio:9076
- Connection: minio:9000

**🔄 N8N** (6 tools) - Workflow automation
- HTTP wrapper to n8n:5678
- 400+ workflow integrations

**⏰ TimescaleDB** (6 tools) - Time-series database
- HTTP wrapper to mcp-timescaledb:48011
- Connection: timescaledb:5432

**📈 Interactive Brokers** (10 tools) - Market data
- HTTP wrapper to mcp-ib:48012
- Paper trading account access

**🗄️ ArangoDB** (7 tools) - Multi-model database
- npx arango-server v0.4.0 (stdio)
- Connection: arangodb:8529/ai_memory

**💾 OpenMemory** (4 tools) - Semantic memory
- HTTP wrapper to mcp-openmemory:8000
- Backend: mem0 v1.0.0 with Gemini embeddings
- Integration: `/cmemory` command

### Network Configuration
- **mcp-net**: External network for MCP service communication
- **postgres-net**: External network for PostgreSQL database access
- **arangodb-net**: External network for ArangoDB access
- **timescaledb-net**: External network for TimescaleDB access
- **mcp-ib-net**: External network for Interactive Brokers access
- **minio-net**: External network for MinIO access
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
All services accessible via TBXark proxy at `http://localhost:9090/[service]/mcp`:

- **Filesystem**: `http://localhost:9090/filesystem/mcp`
- **PostgreSQL**: `http://localhost:9090/postgres/mcp`
- **Playwright**: `http://localhost:9090/playwright/mcp`
- **Memory**: `http://localhost:9090/memory/mcp`
- **MinIO**: `http://localhost:9090/minio/mcp`
- **N8N**: `http://localhost:9090/n8n/mcp`
- **TimescaleDB**: `http://localhost:9090/timescaledb/mcp`
- **Interactive Brokers**: `http://localhost:9090/ib/mcp`
- **ArangoDB**: `http://localhost:9090/arangodb/mcp`
- **OpenMemory**: `http://localhost:9090/openmemory/mcp`

### Claude Code CLI Registration
```bash
# Register all services (example)
claude mcp add filesystem http://localhost:9090/filesystem/mcp -t http
claude mcp add postgres http://localhost:9090/postgres/mcp -t http
claude mcp add playwright http://localhost:9090/playwright/mcp -t http
claude mcp add memory http://localhost:9090/memory/mcp -t http
claude mcp add openmemory http://localhost:9090/openmemory/mcp -t http
# ... add other services as needed

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

# Test OpenMemory - list tools
curl -X POST http://localhost:9090/openmemory/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"3","method":"tools/list","params":{}}'

# Test OpenMemory - add memory
curl -X POST http://localhost:9090/openmemory/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"4","method":"tools/call","params":{"name":"add_memory","arguments":{"text":"Test memory","category":"note"}}}'
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

### OpenMemory Service
- **Container**: mcp-openmemory (FastAPI HTTP server on port 48013)
- **Backend**: OpenMemory REST API at openmemory-api:8765
- **Tools**: 4 operations (add_memory, search_memories, list_memories, delete_memory)
- **Features**: Semantic search with Gemini embeddings (768-dim), AI categorization, Qdrant vector storage
- **Network**: Requires mcp-net for API connectivity
- **Integration**: Used by `/cmemory` slash command for saving lessons learned
- **Documentation**: `/home/administrator/projects/mcp/openmemory/CLAUDE.md`

### Other Services
For detailed information about remaining services (Playwright, Memory, MinIO, N8N, TimescaleDB, IB, ArangoDB):
- See main MCP documentation: `/home/administrator/projects/mcp/CLAUDE.md`
- Individual service docs: `/home/administrator/projects/mcp/[service]/CLAUDE.md` or `AI.md`

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

### MCP Code Executor (Client, Not a Server)
- **Container**: mcp-code-executor (port 9091)
- **Role**: MCP CLIENT that consumes tools from this proxy
- **Purpose**: Sandboxed TypeScript/Python execution environment
- **Architecture**: code-executor → mcp-proxy → MCP servers
- **Usage**: Used by Claude Code for multi-tool workflows
- **Documentation**: `/home/administrator/projects/mcp/code-executor/CLAUDE.md`

**IMPORTANT**: Code-executor is NOT an MCP server. It's a client that calls MCP tools through this proxy.

### Individual MCP Containers
- **mcp-playwright**: Browser automation (port 8000)
- **mcp-minio**: S3 storage interface (port 9076)
- **mcp-timescaledb**: Time-series queries (port 48011)
- **mcp-ib**: Interactive Brokers market data (port 48012)
- **mcp-openmemory**: Semantic memory operations (port 48013)

### Backend Infrastructure
- **PostgreSQL**: Main database server at postgres:5432
- **TimescaleDB**: Time-series database at timescaledb:5432
- **ArangoDB**: Multi-model database at arangodb:8529
- **OpenMemory API**: mem0 backend at openmemory-api:8765
- **MinIO**: S3 storage at minio:9000
- **N8N**: Workflow automation at n8n:5678
- **Qdrant**: Vector database for embeddings

### Docker Networks
- **mcp-net**: Primary MCP service communication
- **postgres-net**: PostgreSQL database access
- **arangodb-net**: ArangoDB access
- **timescaledb-net**: TimescaleDB access
- **mcp-ib-net**: Interactive Brokers access
- **minio-net**: MinIO storage access

## 📚 Documentation References
- **Planning**: `/home/administrator/projects/mcp/planhttp.md`
- **Status**: `/home/administrator/projects/mcp/planhttp.status.md`
- **Fix History**: `/home/administrator/projects/mcp/fixhttp.status.md`
- **Session Notes**: `/home/administrator/projects/AINotes/lastsession.md`

---

**Last Updated**: 2025-11-23
**Status**: ✅ Operational - 10 services, 67 tools, fully tested
**Recent Addition**: OpenMemory MCP integration for semantic memory operations
**Documentation**: See `/home/administrator/projects/mcp/CLAUDE.md` for complete infrastructure overview