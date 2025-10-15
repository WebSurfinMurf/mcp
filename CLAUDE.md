# MCP Infrastructure - Executive Summary

## Overview
Complete Model Context Protocol (MCP) integration providing 57+ tools across 8 specialized servers. Deployed with dual-transport architecture (HTTP proxy for Open WebUI, SSE/stdio for CLI tools) and automatic tool execution middleware.

**Quick Stats:**
- **MCP Servers**: 9 active (filesystem, postgres, puppeteer, memory, minio, n8n, timescaledb, ib, arangodb)
- **Total Tools**: 64 tools available
- **Middleware**: OpenAI-compatible proxy with automatic tool execution loop
- **Architecture**: TBXark MCP Proxy + Custom FastAPI Middleware
- **Proxy Endpoint**: `http://localhost:9090` (all servers accessible via `/[server]/mcp`)

---

## Architecture

### Component Stack
```
Open WebUI (port 8090)
    ↓ HTTPS via Traefik
LiteLLM (port 4000)
    ↓ Optional (for MCP tools)
MCP Middleware (port 4001/8080)
    ↓ JSON-RPC
TBXark MCP Proxy (port 9090)
    ↓ stdio/SSE
Individual MCP Servers (7 services)
```

### Key Components

**TBXark MCP Proxy** (`projects/mcp/proxy/`)
- HTTP gateway exposing MCP servers via REST endpoints
- Routes: `/[server-name]/mcp` (e.g., `/postgres/mcp`)
- Translates HTTP to MCP stdio protocol

**MCP Middleware** (`projects/mcp/middleware/`)
- OpenAI-compatible `/v1/chat/completions` endpoint
- Automatic tool injection (48 tools)
- Tool execution loop (max 5 iterations)
- Model naming: adds `-mcp` suffix for UI differentiation

**Individual MCP Servers** (`projects/mcp/[service]/`)
- Native MCP protocol implementations
- Dual transport: SSE for Claude Code CLI, stdio via bridges for Codex

---

## MCP Servers

### 📁 Filesystem (9 tools)
- Workspace: `/workspace` (read-only), `/tmp` (read-write)
- Tools: list, read, write, search, move, info
- Path translation: host ↔ container

### 🗄️ PostgreSQL (1 tool)
- Connection: postgres:5432/postgres
- Tool: execute_sql (restricted mode)
- Primary database operations

### 🌐 Puppeteer (7 tools)
- Headless Chromium automation
- Tools: navigate, screenshot, click, evaluate, console
- Browser-based web interaction

### 🧠 Memory (9 tools)
- KG (Knowledge Graph) memory storage
- Tools: entities, relations, search, open_nodes
- Persistent context storage

### 🪣 MinIO (9 tools)
- S3-compatible object storage
- Tools: buckets, objects, upload, download, metadata
- Connection: minio:9000
- Container: mcp-minio (port 9076)
- Networks: minio-net, mcp-net

### 🔄 N8N (6 tools)
- Workflow automation (400+ integrations)
- Tools: workflows, execute, executions, credentials
- Connection: n8n:5678

### ⏰ TimescaleDB (6 tools)
- Time-series database operations
- Tools: execute_query, list_databases, list_tables, describe_table, get_table_stats, list_hypertables
- Connection: timescaledb:5432
- Container: mcp-timescaledb (port 48011)
- Networks: mcp-net (added 2025-10-10 for proxy access)

### 📈 Interactive Brokers (10 tools)
- Market data and portfolio operations for paper trading
- Tools: lookup_contract, ticker_to_conid, get_historical_data, search_contracts, get_historical_news, get_article, get_fundamental_data, get_account_summary, get_positions, get_contract_details
- Connection: IB Gateway (paper trading account)
- Container: mcp-ib (port 48012), mcp-ib-gateway (ports 14002 API, 15900 VNC)
- Networks: mcp-ib-net (internal), mcp-net (proxy access)
- Architecture: FastAPI HTTP wrapper around ib-mcp stdio server

### 🗄️ ArangoDB (7 tools) - ✅ DEPLOYED
- Multi-model database (document, graph, key-value) for AI memory storage
- Tools: arango_query, arango_insert, arango_update, arango_remove, arango_list_collections, arango_create_collection, arango_backup
- Connection: arangodb:8529
- Target Database: ai_memory (AI context/memory storage)
- Package: arango-server v0.4.0 by ravenwits (TypeScript)
- Integration: Via MCP Proxy (stdio transport, no separate container)
- Networks: MCP proxy on arangodb-net for database access
- Status: Fully operational (deployed 2025-10-14)
- Documentation: `/home/administrator/projects/mcp/arangodb/AI.md`

---

## Open WebUI Integration

### Dual Model Configuration
Open WebUI offers two model choices:
1. **claude-sonnet-4-5**: Direct LiteLLM (no MCP tools)
2. **claude-sonnet-4-5-mcp**: Via middleware (64 MCP tools)

### Configuration
**Admin Settings → Connections:**
- Connection 0: `http://litellm:4000/v1` (direct)
- Connection 1: `http://mcp-middleware:8080/v1` (MCP-enabled)

**Networks Required:**
- Open WebUI must be on `litellm-mcp-net` network
- Middleware must be on `mcp-net` and `litellm-mcp-net`

### Special Commands
- **"list tools"**: Triggers `mcp_list_all_tools` function
- Returns formatted markdown table organized by server
- Shows all 64 tools with descriptions

---

## Middleware Details

### Tool Execution Loop
1. Inject 64 MCP tools into request
2. Call LiteLLM with tools enabled
3. If response contains tool_calls:
   - Execute each tool via MCP proxy
   - Add results to conversation
   - Loop back to step 2
4. Return final answer after tool execution completes

### Tool Naming Convention
- Format: `mcp_[server]_[toolname]`
- Example: `mcp_postgres_execute_sql`
- Middleware routes to correct MCP server automatically

### Endpoints
- `/v1/chat/completions`: Main proxy with tool execution
- `/v1/models`: Lists models with `-mcp` suffix
- `/health`: Service health + tool counts
- `/reload`: Reload tools from all MCP servers

---

## Deployment

### Quick Start
```bash
# Start TBXark MCP Proxy
cd /home/administrator/projects/mcp/proxy
docker compose up -d

# Start Middleware
cd /home/administrator/projects/mcp/middleware
docker compose up -d

# Verify health
curl http://localhost:4001/health
```

### Network Setup
```bash
# Connect Open WebUI to middleware network
docker network connect litellm-mcp-net open-webui

# Verify connectivity
docker exec open-webui curl http://mcp-middleware:8080/health
```

### Configuration Files
- Proxy: `projects/mcp/proxy/config.json` (MCP server definitions)
- Middleware: `projects/mcp/middleware/main.py` (tool execution logic)
- LiteLLM: `projects/litellm/config/config.yaml` (model config)

---

## Usage Patterns

### From Open WebUI
1. Select **claude-sonnet-4-5-mcp** model
2. Ask natural language questions
3. Claude automatically calls appropriate MCP tools
4. Middleware executes tools and returns results

### Example Queries
```
"list tools" → Shows all 64 MCP tools organized by server
"list postgres databases" → Calls mcp_postgres_execute_sql
"read the config file" → Calls mcp_filesystem_read_file
"take screenshot of example.com" → Calls mcp_puppeteer_navigate + screenshot
"upload file to minio" → Calls mcp_minio_upload_object
"query timescaledb" → Calls mcp_timescaledb_execute_query
"get AAPL historical data" → Calls mcp_ib_get_historical_data
"show my portfolio positions" → Calls mcp_ib_get_positions
"list collections in ArangoDB" → Calls mcp_arangodb_list_collections
"query the ai_memory database" → Calls mcp_arangodb_query
"insert document into ArangoDB" → Calls mcp_arangodb_insert
```

### From Kilo Code (VS Code Extension)
```json
{
  "mcpServers": {
    "filesystem": {
      "type": "streamable-http",
      "url": "http://linuxserver.lan:9090/filesystem/mcp"
    },
    "postgres": {
      "type": "streamable-http",
      "url": "http://linuxserver.lan:9090/postgres/mcp"
    },
    "puppeteer": {
      "type": "streamable-http",
      "url": "http://linuxserver.lan:9090/puppeteer/mcp"
    },
    "memory": {
      "type": "streamable-http",
      "url": "http://linuxserver.lan:9090/memory/mcp"
    },
    "minio": {
      "type": "streamable-http",
      "url": "http://linuxserver.lan:9090/minio/mcp"
    },
    "n8n": {
      "type": "streamable-http",
      "url": "http://linuxserver.lan:9090/n8n/mcp"
    },
    "timescaledb": {
      "type": "streamable-http",
      "url": "http://linuxserver.lan:9090/timescaledb/mcp"
    },
    "ib": {
      "type": "streamable-http",
      "url": "http://linuxserver.lan:9090/ib/mcp"
    },
    "arangodb": {
      "type": "streamable-http",
      "url": "http://linuxserver.lan:9090/arangodb/mcp"
    }
  }
}
```

### From Claude Code CLI
```bash
# Register MCP servers (SSE transport or HTTP via proxy)
claude mcp add postgres-direct http://127.0.0.1:48010/sse --transport sse
claude mcp add filesystem http://127.0.0.1:9073/sse --transport sse
# ... etc for all SSE servers

# Note: ArangoDB integrated via proxy, accessible via HTTP transport
```

---

## Monitoring & Health

### Health Checks
```bash
# Middleware health
curl http://localhost:4001/health
# Returns: servers count, total tools, tools per server

# Proxy health
docker logs mcp-proxy --tail 20

# Individual server health (example: postgres)
curl -X POST http://localhost:9090/postgres/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}'

# IB server health (direct endpoint)
curl http://localhost:48012/health

# IB server via proxy
curl -X POST http://localhost:9090/ib/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

### Logs
```bash
# Middleware logs (shows tool execution)
docker logs mcp-middleware -f

# Open WebUI logs (shows requests)
docker logs open-webui -f

# LiteLLM logs
docker logs litellm -f
```

---

## Best Practices

### For AI Assistants
1. Always use MCP tools over shell commands when available
2. Use natural language requests ("list tools", "read file X")
3. Let middleware handle tool routing automatically

### Tool Selection Priority
1. **Database** → postgres or timescaledb
2. **AI Memory/Context** → arangodb (multi-model database)
3. **Files** → filesystem
4. **Web** → puppeteer
5. **Storage** → minio
6. **Automation** → n8n
7. **Memory** → memory (legacy KG store)
8. **Market Data** → ib (Interactive Brokers)

### Security Notes
- All MCP servers run in isolated Docker networks
- Filesystem: read-only workspace, write-only /tmp
- Database: restricted mode (read-only)
- No direct internet access from MCP containers

---

## Troubleshooting

### "No models in dropdown"
- Verify Open WebUI is on `litellm-mcp-net` network
- Check middleware health endpoint responds

### "Tools not executing"
- Verify using `-mcp` model variant
- Check middleware logs for tool execution
- Ensure MCP proxy is running

### "Can't distinguish models"
- Both models show as same name in UI
- Look for `-mcp` suffix in model ID
- Use second connection for MCP tools

---

## Documentation
- **Deployment Guide**: `projects/mcp/directmcp.md`
- **Proxy Config**: `projects/mcp/proxy/config.json`
- **Middleware**: `projects/mcp/middleware/main.py`
- **Individual Services**: `projects/mcp/[service]/AI.md`
- **Planned Services**: `projects/mcp/arangodb/AI.md` (Phase 2 planning)

## Kilo Code Integration

**Validated**: 2025-10-14
**Status**: ✅ All 9 servers tested and working via TBXark proxy

### Configuration Location
- **Global**: `~/.config/Code/User/globalStorage/kilocode.kilo-code/mcp_settings.json`
- **Project**: `.kilocode/mcp.json` (in project root)

### Key Features
- **Streamable HTTP Transport**: All servers accessible via single proxy endpoint
- **Auto-discovery**: Tools automatically loaded from each server
- **64 Total Tools**: Full access to all MCP capabilities
- **Network Access**: Works from external machines via `linuxserver.lan:9090`

### Troubleshooting
- If server doesn't appear in UI, check Kilo Code output panel for connection errors
- Verify proxy is running: `docker ps --filter name=mcp-proxy`
- Test endpoint: `curl http://linuxserver.lan:9090/[server]/mcp`

---

## Recent Deployments

### ArangoDB MCP Server (Phase 2) - ✅ COMPLETE
**Deployment Date**: 2025-10-14
**Status**: ✅ Fully Operational

**Implementation:**
- Using standard `arango-server` v0.4.0 by ravenwits (TypeScript package)
- Integrated via MCP Proxy (stdio transport, no separate container needed)
- 7 tools available: query, insert, update, remove, list_collections, create_collection, backup
- Connected to ArangoDB 3.11.14 backend (ai_memory database)
- MCP proxy added to arangodb-net for database access

**Tools Added:**
1. `arango_query` - Execute AQL queries
2. `arango_insert` - Insert documents
3. `arango_update` - Update documents
4. `arango_remove` - Remove documents
5. `arango_list_collections` - List collections
6. `arango_create_collection` - Create collections
7. `arango_backup` - Backup to JSON files

**Benefits Achieved:**
- AI memory/context storage capabilities
- Document database operations for conversation history
- Collection management for organized data storage
- Backup functionality for data persistence

---

**Project Status**: ✅ Production (9 servers, 64 tools, automatic execution)
**Last Updated**: 2025-10-14 (ArangoDB MCP integration complete)