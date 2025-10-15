# MCP ArangoDB Server

## Status: ✅ DEPLOYED (2025-10-14)

This MCP server provides database interaction capabilities for ArangoDB multi-model database, enabling AI memory/context storage, graph operations, and document queries.

---

## Overview

**Purpose**: Provide MCP tool access to ArangoDB multi-model database for AI memory/context storage, graph operations, and document queries.

**Implementation**: Standard `arango-server` v0.4.0 by ravenwits (TypeScript)
**Database**: ArangoDB 3.11.14 (deployed 2025-10-14)
**Target Database**: `ai_memory`
**MCP Server**: Integrated via MCP Proxy (stdio transport)
**Tools Available**: 7 database operations

---

## Architecture

### Component Design

```
MCP Clients (Open WebUI, Kilo Code, Claude Code)
                     ↓
              MCP Proxy (9090)
                     ↓
         arango-server (stdio via npx)
                     ↓
            arangodb:8529 (ai_memory database)
```

### Implementation

**Deployment Method**: Integrated via MCP Proxy (no standalone container needed)
**Package**: `arango-server` (npm package, v0.4.0)
**Transport**: stdio (via npx command in proxy)
**Networks**: MCP proxy is on `arangodb-net` for database access

### Connection Details

**Internal Connection**:
- URL: `http://arangodb:8529`
- Database: `ai_memory`
- Authentication: root user (via environment variables)
- Transport: HTTP API

**External Access**:
- Proxy: `http://localhost:9090/arangodb/mcp` (all MCP clients)
- Direct SSE: Not applicable (stdio-only server)

---

## Available Tools

The `arango-server` package provides 7 MCP tools for ArangoDB operations:

### Query Operations
1. **arango_query** - Execute AQL (ArangoDB Query Language) queries
   - Parameters: `query` (string), `bindVars` (object, optional)
   - Returns: Query results as JSON array
   - Example: `FOR doc IN test_collection RETURN doc`

### Document Operations
2. **arango_insert** - Insert documents into collections
   - Parameters: `collection` (string), `document` (object)
   - Returns: Document metadata (_id, _key, _rev)

3. **arango_update** - Update existing documents
   - Parameters: `collection` (string), `key` (string), `update` (object)
   - Returns: Updated document metadata

4. **arango_remove** - Remove documents from collections
   - Parameters: `collection` (string), `key` (string)
   - Returns: Removed document metadata

### Collection Operations
5. **arango_list_collections** - List all collections in the database
   - Parameters: None
   - Returns: Array of collection information

6. **arango_create_collection** - Create a new collection
   - Parameters: `name` (string), `type` (document/edge, optional), `waitForSync` (boolean, optional)
   - Returns: Collection information (name, type, status)

### Backup Operations
7. **arango_backup** - Backup collections to JSON files
   - Parameters: `outputDir` (string), `collection` (string, optional), `docLimit` (integer, optional)
   - Returns: Success message with backup location

---

## Deployment

### Configuration

**MCP Proxy Config** (`/home/administrator/projects/mcp/proxy/config.json`):
```json
{
  "mcpServers": {
    "arangodb": {
      "command": "npx",
      "args": ["-y", "arango-server"],
      "env": {
        "NODE_NO_WARNINGS": "1",
        "ARANGO_URL": "http://arangodb:8529",
        "ARANGO_DB": "ai_memory",
        "ARANGO_USERNAME": "root",
        "ARANGO_PASSWORD": "4SlfiYq6XOUZWP7jKakBksrudBhSWIqV"
      }
    }
  }
}
```

**MCP Proxy Networks** (`/home/administrator/projects/mcp/proxy/docker-compose.yml`):
- Added `arangodb-net` to allow proxy to access ArangoDB container

### Testing

**List available tools**:
```bash
curl -X POST http://localhost:9090/arangodb/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}'
```

**List collections**:
```bash
curl -X POST http://localhost:9090/arangodb/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"arango_list_collections","arguments":{}}}'
```

**Execute AQL query**:
```bash
curl -X POST http://localhost:9090/arangodb/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"3","method":"tools/call","params":{"name":"arango_query","arguments":{"query":"FOR doc IN test_collection RETURN doc"}}}'
```

### Integration with MCP Clients

**Kilo Code** (VS Code extension):
```json
{
  "mcpServers": {
    "arangodb": {
      "type": "streamable-http",
      "url": "http://linuxserver.lan:9090/arangodb/mcp"
    }
  }
}
```

**Open WebUI**:
- Select `claude-sonnet-4-5-mcp` model
- ArangoDB tools automatically available via middleware
- Use natural language: "list collections in ArangoDB" or "query the ai_memory database"

**Claude Code CLI**:
- Accessible via MCP proxy (http transport)
- Tools injected automatically when using proxy integration

---

## Use Cases

### AI Context Storage
Store conversation history, embeddings, and context in document collections:
```
ai_memory/
├── conversations/      # Document collection
├── embeddings/        # Document collection with vector data
├── context_graph/     # Graph for relationships
└── entities/          # Named entities from conversations
```

### Knowledge Graph
Build semantic knowledge graphs:
```
ai_memory/
├── concepts/          # Vertex collection
├── relationships/     # Edge collection
└── knowledge_graph/   # Named graph
```

### Session Management
Track user sessions and preferences:
```
ai_memory/
├── sessions/          # Active sessions
├── user_preferences/  # User settings
└── history/          # Historical queries
```

---

## Security Considerations

### Service Account Permissions
Create dedicated MCP service account with:
- ✅ Read/write to `ai_memory` database only
- ❌ No access to `_system` database
- ❌ No user management permissions
- ❌ No database creation/deletion

### Network Isolation
- ✅ MCP server on `arangodb-net` (can access ArangoDB backend)
- ✅ MCP server on `mcp-net` (can communicate with proxy)
- ❌ NOT on `traefik-net` (no direct internet exposure)

### Credentials
- Store in `/home/administrator/projects/secrets/mcp-arangodb.env`
- Use secure password generation
- Never commit to git

---

## Expected Tool Count

**Estimated**: 10-12 tools
- 3 database/collection operations
- 1 AQL query execution
- 4 document CRUD operations
- 3 graph operations
- 1 schema inspection

**Total MCP Infrastructure After Deployment**: 9 servers, 67-69 tools

---

## Naming Convention Compliance

✅ **MCP Server**: `mcp-arangodb` (follows pattern)
✅ **Container**: `mcp-arangodb` (matches server name)
✅ **Network**: Uses existing `arangodb-net` and `mcp-net`
✅ **Directory**: `/home/administrator/projects/mcp/arangodb/`
✅ **Target Database**: `ai_memory` (descriptive, not "arangodb")

---

## Integration with Existing Infrastructure

### Similar to mcp-postgres Pattern
- Single MCP server for entire ArangoDB instance
- Database name passed as parameter to tools
- Can access multiple databases (ai_memory, future databases)
- Service account with limited permissions

### Dual Transport (like other MCP servers)
- **SSE**: Direct access for Claude Code CLI (port 48013)
- **Proxy**: Routed access for middleware/Kilo Code (via port 9090)

### Middleware Auto-Discovery
- Tools automatically loaded via `/tools/list` endpoint
- Middleware injects tools into OpenAI format
- No manual tool registration needed

---

## Timeline

**Phase 1**: ✅ COMPLETE (2025-10-14)
- ArangoDB 3.11.14 deployed with OAuth2 authentication
- Database `ai_memory` created
- Documentation completed

**Phase 2**: ✅ COMPLETE (2025-10-14)
- Researched standard MCP servers for ArangoDB
- Selected `arango-server` v0.4.0 by ravenwits (TypeScript, 7 tools)
- Integrated via MCP Proxy (stdio transport, no separate container needed)
- Updated proxy configuration and networks
- Tested all 7 tools successfully
- Documentation updated

**Actual Effort**: ~2 hours (investigation + configuration + testing)

---

## References

### Internal Documentation
- **ArangoDB Deployment**: `/home/administrator/projects/arangodb/CLAUDE.md`
- **System Overview**: `/home/administrator/projects/AINotes/SYSTEM-OVERVIEW.md`
- **MCP Infrastructure**: `/home/administrator/projects/mcp/CLAUDE.md`
- **Example MCP Server**: `/home/administrator/projects/mcp/postgres/AI.md`

### External Resources
- **ArangoDB Python Driver**: https://docs.python-arango.com/
- **ArangoDB HTTP API**: https://docs.arangodb.com/stable/develop/http-api/
- **AQL Reference**: https://docs.arangodb.com/stable/aql/
- **MCP Specification**: https://modelcontextprotocol.io/

---

## Questions to Resolve

1. **MCP Server Implementation**: Build custom or search for community version?
   - **Decision**: Build custom FastAPI wrapper (more control, consistent with infrastructure)

2. **Tool Scope**: Start with basic CRUD or include advanced graph operations?
   - **Recommendation**: Start with core operations (queries, CRUD), add graph features later

3. **Service Account**: Limit to ai_memory only or allow multiple databases?
   - **Recommendation**: Allow multiple databases (passed as parameter), restrict permissions per database

4. **Graph Features**: How deep should graph traversal capabilities go?
   - **Recommendation**: Basic traversal and shortest path initially, expand based on usage

---

**Status**: ✅ Fully Deployed and Operational
**Total Tools**: 7 ArangoDB operations
**Total MCP Infrastructure**: 9 servers, 64 tools (updated 2025-10-14)
**Integration**: Open WebUI, Kilo Code, Claude Code CLI

---

*Document created: 2025-10-14*
*Last updated: 2025-10-14 (Phase 2 completed)*
*Deployment: Standard arango-server via MCP Proxy*
