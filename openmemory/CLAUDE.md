# OpenMemory MCP Server

## 📋 Project Overview
MCP server providing semantic memory operations through mem0 (OpenMemory) with AI-powered search and categorization. Translates MCP protocol to OpenMemory REST API, enabling universal access from Claude Code, Open WebUI, laptop, and any MCP-compatible client.

## 🟢 Current State (2025-11-23)
- **Status**: ✅ Operational - Full semantic memory with embeddings
- **OpenMemory Version**: mem0 v1.0.0
- **Container**: mcp-openmemory (port 48013)
- **Proxy Endpoint**: `http://localhost:9090/openmemory/mcp`
- **Total Tools**: 4 (add_memory, search_memories, list_memories, delete_memory)

## 📝 Recent Work & Changes

### Session: 2025-11-23 - Initial Deployment Complete
- **Created**: FastAPI MCP server that bridges MCP protocol to OpenMemory REST API
- **Integrated**: With TBXark MCP proxy for universal access
- **Tools**: 4 semantic memory operations with automatic categorization
- **Fixed**: Gemini API key issue (key was reported as leaked)
- **Updated**: `/cmemory` command to use OpenMemory MCP tools
- **Verified**: Full end-to-end functionality (add, search, list memories)

## 🏗️ Architecture

```
Claude Code / Open WebUI / Laptop
        │ (MCP protocol)
        ▼
TBXark Proxy (localhost:9090/openmemory/mcp)
        │ (HTTP via wrapper)
        ▼
MCP OpenMemory Server (mcp-openmemory:8000/mcp)
        │ (REST API)
        ▼
OpenMemory API (openmemory-api:8765)
        │
        ├─→ LLM: GPT-5-mini (via LiteLLM)
        ├─→ Embeddings: Gemini text-embedding-004 (768-dim)
        ├─→ Vector Store: Qdrant
        └─→ Database: PostgreSQL (openmemory_db)
```

### Network Configuration
- **mcp-net**: Primary network for MCP services and OpenMemory API access
- Container: mcp-openmemory (communicates with openmemory-api)

## ⚙️ Configuration

### Files
- **Docker Compose**: `/home/administrator/projects/mcp/openmemory/docker-compose.yml`
- **Server Code**: `/home/administrator/projects/mcp/openmemory/src/server.py`
- **Proxy Wrapper**: `/home/administrator/projects/mcp/proxy/wrappers/openmemory-wrapper.sh`
- **Proxy Config**: `/home/administrator/projects/mcp/proxy/config.json` (openmemory entry)
- **Dockerfile**: `/home/administrator/projects/mcp/openmemory/Dockerfile`

### Environment Variables
Default values (no env file required):
```bash
OPENMEMORY_API=http://openmemory-api:8765  # OpenMemory REST API endpoint
OPENMEMORY_USER=administrator               # User ID for memories
OPENMEMORY_APP=claude-code                  # App name for memory organization
```

### Docker Compose Service

**mcp-openmemory** (HTTP MCP server):
- Image: Custom build (Python 3.12 + FastAPI + requests)
- Port: 48013:8000
- Networks: mcp-net
- Health check: HTTP GET /health

## 🌐 Access & Management

### Service Endpoints
- **Via Proxy**: `http://localhost:9090/openmemory/mcp` (recommended)
- **Direct HTTP**: `http://localhost:48013/mcp`
- **Health Check**: `http://localhost:48013/health`

### Available Tools (4 total)

#### 1. add_memory
Add new memory with automatic categorization and semantic indexing.
```typescript
await callMCPTool('openmemory', 'add_memory', {
  text: "The memory content to store",
  category: "gotcha|lesson|solution|decision|preference|fact|note",
  metadata: { project: "name", timestamp: "...", ... }
});
```

**Parameters**:
- `text` (required): Memory content
- `category` (optional): gotcha, lesson, solution, decision, preference, fact, note
- `metadata` (optional): Additional context as JSON object

#### 2. search_memories
Semantic search using AI embeddings - finds relevant memories by meaning.
```typescript
const results = await callMCPTool('openmemory', 'search_memories', {
  query: "deployment patterns",
  limit: 10,
  category: "lesson"
});
```

**Parameters**:
- `query` (required): Natural language search query
- `limit` (optional): Max results (default: 10)
- `category` (optional): Filter by category

#### 3. list_memories
List all memories with filtering and pagination.
```typescript
const memories = await callMCPTool('openmemory', 'list_memories', {
  category: "gotcha",
  search_query: "docker",
  page: 1,
  size: 50
});
```

**Parameters**:
- `category` (optional): Filter by category
- `search_query` (optional): Text filter
- `page` (optional): Page number (default: 1)
- `size` (optional): Page size (default: 50, max: 100)

#### 4. delete_memory
Delete a specific memory by ID (use with caution).
```typescript
await callMCPTool('openmemory', 'delete_memory', {
  memory_id: "uuid-here"
});
```

**Parameters**:
- `memory_id` (required): UUID of memory to delete

### Testing Tools

#### Via Proxy (Recommended)
```bash
# List tools
curl -X POST http://localhost:9090/openmemory/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}'

# Add memory
curl -X POST http://localhost:9090/openmemory/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc":"2.0","id":"2","method":"tools/call",
    "params":{
      "name":"add_memory",
      "arguments":{
        "text":"Docker containers must be on same network to communicate",
        "category":"lesson",
        "metadata":{"project":"infrastructure","date":"2025-11-23"}
      }
    }
  }'

# Search memories
curl -X POST http://localhost:9090/openmemory/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc":"2.0","id":"3","method":"tools/call",
    "params":{
      "name":"search_memories",
      "arguments":{"query":"docker networking","limit":5}
    }
  }'

# List all memories
curl -X POST http://localhost:9090/openmemory/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc":"2.0","id":"4","method":"tools/call",
    "params":{"name":"list_memories","arguments":{}}
  }'
```

## 🔗 Integration Points

### TBXark MCP Proxy
Added to `/home/administrator/projects/mcp/proxy/config.json`:
```json
{
  "mcpServers": {
    "openmemory": {
      "command": "/wrappers/openmemory-wrapper.sh",
      "args": []
    }
  }
}
```

Wrapper script (`/home/administrator/projects/mcp/proxy/wrappers/openmemory-wrapper.sh`):
- Forwards STDIO MCP protocol to HTTP endpoint (mcp-openmemory:8000/mcp)
- Enables SSE/streamable HTTP transport for all MCP clients

### Claude Code CLI
The `/cmemory` slash command uses OpenMemory MCP tools:
- Location: `/home/administrator/.claude/commands/cmemory.md`
- Automatically discovers and uses openmemory MCP server
- Provides guided memory capture workflow

### From Code Executor
```typescript
import { callMCPTool } from '/app/client.js';

// Add memory
await callMCPTool('openmemory', 'add_memory', {
  text: "Lesson learned here",
  category: "lesson",
  metadata: { project: "mcp" }
});

// Search
const results = await callMCPTool('openmemory', 'search_memories', {
  query: "what did I learn about MCP?",
  limit: 5
});
```

### From Open WebUI
Uses middleware with automatic tool discovery:
- Model: `claude-sonnet-4-5-mcp`
- Tools automatically injected
- Natural language: "Save this to memory: ..."

### From Laptop (Kilo Code)
Add to `.kilocode/mcp.json`:
```json
{
  "mcpServers": {
    "openmemory": {
      "type": "streamable-http",
      "url": "http://linuxserver.lan:9090/openmemory/mcp"
    }
  }
}
```

## 🛠️ Operations

### Container Management
```bash
# Start service
cd /home/administrator/projects/mcp/openmemory
docker compose up -d

# Check status
docker ps --filter name=mcp-openmemory
docker logs mcp-openmemory --tail 50

# Restart service
docker compose restart

# Stop service
docker compose down
```

### Health Checks
```bash
# MCP server health
curl http://localhost:48013/health

# Check OpenMemory API connectivity
docker exec mcp-openmemory curl -s http://openmemory-api:8765/api/v1/config/ | jq .

# Test via proxy
curl -X POST http://localhost:9090/openmemory/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"health","method":"tools/list","params":{}}'
```

## 🔧 Troubleshooting

### Common Issues

**"unhealthy" status**:
- **Symptom**: Health check returns "unhealthy"
- **Cause**: Cannot reach openmemory-api
- **Solution**: Ensure both containers on mcp-net network
- **Verification**: `docker network inspect mcp-net | grep -E "mcp-openmemory|openmemory-api"`

**"403 PERMISSION_DENIED" from Gemini**:
- **Symptom**: Embeddings fail with "API key was reported as leaked"
- **Cause**: Gemini API key blocked by Google
- **Solution**: Get new API key from https://aistudio.google.com/app/apikey
- **Fix**: Update GEMINI_API_KEY in `/home/administrator/projects/secrets/openmemory.env`
- **Restart**: `cd /home/administrator/projects/openmemory && docker compose restart openmemory-api`

**MCP tools not showing up**:
- **Symptom**: Tools list is empty or openmemory not found
- **Cause**: Proxy not reloaded after config change
- **Solution**: Restart MCP proxy
- **Fix**: `cd /home/administrator/projects/mcp/proxy && docker compose restart`

**Search returns no results**:
- **Symptom**: search_memories returns empty array
- **Cause**: User ID mismatch or no memories stored
- **Solution**: Verify user ID matches (default: "administrator")
- **Check**: Use list_memories to see what's actually stored

### Diagnostic Commands
```bash
# Check environment variables
docker exec mcp-openmemory env | grep OPENMEMORY

# Verify network connectivity
docker exec mcp-openmemory getent hosts openmemory-api  # Should resolve

# Check OpenMemory API health
curl http://localhost:8765/api/v1/config/ | jq .

# View full server logs
docker logs mcp-openmemory --since 5m

# Test direct API call (bypass MCP)
curl -X POST http://localhost:48013/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"test","method":"tools/list","params":{}}'
```

## 📋 Standards & Best Practices

### Memory Categories
- **gotcha**: Things commonly forgotten or that trip people up
- **lesson**: Knowledge gained from experience
- **solution**: How we solved a specific problem
- **decision**: Why we chose approach A over B
- **preference**: User's preferred way of doing things
- **fact**: Important factual information
- **note**: General notes and observations

### Metadata Best Practices
Always include:
- `project`: Project/service name
- `date` or `timestamp`: When discovered
- `context`: Additional situational context

### Security Considerations
- **User Isolation**: Memories scoped by user_id (administrator)
- **App Isolation**: Memories organized by app (claude-code)
- **API Access**: Limited to Docker network (mcp-net)
- **No Authentication**: Currently relies on network isolation

## 🔄 Related Services

### OpenMemory (Parent Service)
- **Container**: openmemory-api (port 8765)
- **Database**: PostgreSQL (openmemory_db)
- **Vector Store**: Qdrant
- **Embeddings**: Gemini text-embedding-004
- **Documentation**: `/home/administrator/projects/openmemory/CLAUDE.md`

### Other MCP Services
- **Filesystem**: File operations (9 tools)
- **PostgreSQL**: Database queries (8 tools)
- **Playwright**: Browser automation (6 tools)
- **Memory**: Knowledge graph (9 tools) - different from OpenMemory
- **MinIO**: S3 storage (9 tools)
- **N8N**: Workflow automation (6 tools)
- **TimescaleDB**: Time-series data (6 tools)
- **IB**: Market data (10 tools)
- **ArangoDB**: Multi-model database (7 tools)

### Infrastructure
- **TBXark Proxy**: Unified MCP gateway on port 9090
- **Docker Network**: mcp-net (external, shared)

## 📚 Documentation References
- **Main MCP Documentation**: `/home/administrator/projects/mcp/CLAUDE.md`
- **OpenMemory Service**: `/home/administrator/projects/openmemory/CLAUDE.md`
- **Proxy Config**: `/home/administrator/projects/mcp/proxy/config.json`
- **Claude Command**: `/home/administrator/.claude/commands/cmemory.md`

---

**Last Updated**: 2025-11-23
**Status**: ✅ Operational - Semantic memory with embeddings working
**Integration**: Universal access via MCP protocol (server, laptop, Open WebUI)
**Next Steps**: Use via `/cmemory` command to save lessons learned
