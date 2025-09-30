# MCP Infrastructure - Executive Summary

## Overview
Complete Model Context Protocol (MCP) integration providing 48+ tools across 7 specialized servers. Deployed with dual-transport architecture (HTTP proxy for Open WebUI, SSE/stdio for CLI tools) and automatic tool execution middleware.

**Quick Stats:**
- **MCP Servers**: 7 (filesystem, postgres, puppeteer, memory, minio, n8n, timescaledb)
- **Total Tools**: 48+ specialized capabilities
- **Middleware**: OpenAI-compatible proxy with automatic tool execution loop
- **Architecture**: TBXark MCP Proxy + Custom FastAPI Middleware

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

### 🔄 N8N (6 tools)
- Workflow automation (400+ integrations)
- Tools: workflows, execute, executions, credentials
- Connection: n8n:5678

### ⏰ TimescaleDB (6 tools)
- Time-series database operations
- Tools: execute_sql, schemas, objects, explain
- Connection: timescaledb:5432

---

## Open WebUI Integration

### Dual Model Configuration
Open WebUI offers two model choices:
1. **claude-sonnet-4-5**: Direct LiteLLM (no MCP tools)
2. **claude-sonnet-4-5-mcp**: Via middleware (48 MCP tools)

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
- Shows all 48 tools with descriptions

---

## Middleware Details

### Tool Execution Loop
1. Inject 48 MCP tools into request
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
"list tools" → Shows all 48 MCP tools organized by server
"list postgres databases" → Calls mcp_postgres_execute_sql
"read the config file" → Calls mcp_filesystem_read_file
"take screenshot of example.com" → Calls mcp_puppeteer_navigate + screenshot
```

### From Claude Code CLI
```bash
# Register MCP servers (SSE transport)
claude mcp add postgres-direct http://127.0.0.1:48010/sse --transport sse
claude mcp add filesystem http://127.0.0.1:9073/sse --transport sse
# ... etc for all servers
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

# Individual server health
curl -X POST http://localhost:9090/postgres/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}'
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
2. **Files** → filesystem
3. **Web** → puppeteer
4. **Storage** → minio
5. **Automation** → n8n
6. **Memory** → memory

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

**Project Status**: ✅ Production (7 servers, 48 tools, automatic execution)
**Last Updated**: 2025-09-30