# MCP Code Executor - Project Documentation

**Status**: ✅ Phase 2 Core Complete (2025-11-08)
**Version**: 2.0.0-beta
**Location**: `/home/administrator/projects/mcp/code-executor/`

---

## Overview

**IMPORTANT: This is an MCP CLIENT, not an MCP server.**

Sandboxed TypeScript/Python execution environment that CONSUMES MCP tools via the MCP proxy. Implements progressive disclosure pattern for 85-97% token reduction.

**Architecture Role:**
```
Claude Code → Code Executor (client) → MCP Proxy → MCP Servers
```

Code-executor provides:
- Sandboxed execution environment (TypeScript/Python)
- HTTP API for code execution (port 9091)
- MCP client library for calling tools
- Progressive disclosure API for token efficiency

Code-executor does NOT provide MCP tools - it consumes them from the proxy.

**Production Status**:
- ✅ Phase 1: Core infrastructure (code execution, wrappers, security) - PRODUCTION READY
- ✅ Phase 2: Progressive disclosure API (search, tiered details, metrics) - CORE FEATURES COMPLETE

### Phase 1 Achievements ✅

**Infrastructure Deployed:**
- ✅ Docker container with Node.js 20 + Python 3
- ✅ Fastify HTTP API on port 9091
- ✅ MCP client library (client.ts)
- ✅ TypeScript wrapper generator (generate-wrappers.ts)
- ✅ Executor service (executor.ts)
- ✅ **63 tool wrappers generated** across 9 MCP servers

**Generated Tool Wrappers:**
- filesystem (9 tools)
- postgres (1 tool)
- playwright (6 tools)
- memory (9 tools)
- minio (9 tools)
- n8n (6 tools)
- timescaledb (6 tools)
- ib (10 tools)
- arangodb (7 tools)

### Quick Stats

- **Container**: mcp-code-executor
- **Port**: 9091 (HTTP API)
- **Network**: mcp-net
- **User**: node (UID 1000)
- **Workspace**: /workspace (tmpfs, 500MB)
- **Execution Temp**: /tmp/executions (tmpfs, 100MB, noexec)
- **Resource Limits**: 1 CPU core, 1GB RAM
- **Timeout**: 5 minutes max

---

## API Endpoints

### POST /execute
Execute TypeScript or Python code in sandbox.

**Example:**
```bash
curl -X POST http://localhost:9091/execute \
  -H 'Content-Type: application/json' \
  -d '{"code":"console.log(2+2)"}'
```

**Response:**
```json
{
  "output": "4\n",
  "executionTime": 555,
  "truncated": false
}
```

### GET /health
Service health check with tool inventory.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 26.5,
  "servers": 9,
  "totalTools": 63,
  "toolsByServer": { ... }
}
```

### GET /tools
List all available MCP tool wrappers.

---

## Generated Tool Structure

```
/workspace/servers/
├── arangodb/
│   ├── arango_backup.ts
│   ├── arango_create_collection.ts
│   ├── arango_insert.ts
│   ├── arango_list_collections.ts
│   ├── arango_query.ts
│   ├── arango_remove.ts
│   ├── arango_update.ts
│   └── index.ts
├── filesystem/
│   ├── create_directory.ts
│   ├── get_file_info.ts
│   ├── list_allowed_directories.ts
│   ├── list_directory.ts
│   ├── move_file.ts
│   ├── read_file.ts
│   ├── read_multiple_files.ts
│   ├── search_files.ts
│   ├── write_file.ts
│   └── index.ts
├── [... 7 more servers ...]
└── discovery.ts (utility functions)
```

---

## Usage Patterns

### Pattern 1: Progressive Tool Discovery

```typescript
// Agent discovers available tools on-demand
const { listServers } = await import('/workspace/servers/discovery.js');
const servers = await listServers();
// Returns: ['arangodb', 'filesystem', 'ib', 'memory', 'minio', 'n8n', 'playwright', 'postgres', 'timescaledb']
```

### Pattern 2: Execute MCP Tools via Wrappers

```typescript
(async () => {
  // Import only needed tool wrapper
  const { read_file } = await import('/workspace/servers/filesystem/read_file.js');

  // Call MCP tool
  const content = await read_file({ path: '/workspace/config.json' });
  console.log(content);
})()
```

### Pattern 3: Multi-Tool Composition

```typescript
(async () => {
  const { execute_query } = await import('/workspace/servers/timescaledb/execute_query.js');
  const { upload_object } = await import('/workspace/servers/minio/upload_object.js');

  // Query database
  const result = await execute_query({
    query: "SELECT * FROM metrics WHERE timestamp > NOW() - INTERVAL '1 day'"
  });

  // Filter in execution environment (not in model context!)
  const critical = result.rows.filter(m => m.value > 100);

  // Upload to S3
  const csv = critical.map(r => Object.values(r).join(',')).join('\\n');
  await upload_object({
    bucket: 'exports',
    key: `export-${Date.now()}.csv`,
    content: csv
  });

  console.log(`Exported ${critical.length} critical metrics`);
})()
```

---

## Deployment

### Build and Start

```bash
cd /home/administrator/projects/mcp/code-executor
docker compose build
docker compose up -d
```

### Generate Tool Wrappers

```bash
# Fix permissions first (tmpfs mounted as root)
docker exec -u root mcp-code-executor chown -R node:node /workspace /tmp/executions

# Generate wrappers
docker exec mcp-code-executor npm run generate-wrappers
```

### Health Check

```bash
curl http://localhost:9091/health | jq
```

---

## Security Model

### Sandbox Restrictions

✅ **Enforced:**
- Non-root user (node, UID 1000)
- Network isolation (mcp-net only, no internet)
- Resource limits (1 CPU, 1GB RAM)
- Execution timeout (5 minutes)
- Output size limit (100KB)
- Read-only root filesystem
- no-new-privileges

❌ **Blocked:**
- Internet access
- Docker commands
- System administration
- Binary execution from /tmp (noexec)
- Privilege escalation

### Filesystem Access

- `/workspace` - Read/write (tmpfs, ephemeral)
- `/tmp/executions` - Write-only for code execution (tmpfs, noexec)
- Rest of filesystem - Read-only

---

## Implementation Status

### ✅ Phase 1 Complete (2025-11-08)

**Deliverables:**
1. ✅ Docker container with sandbox (Dockerfile, docker-compose.yml)
2. ✅ MCP client library (client.ts)
3. ✅ TypeScript wrapper generator (generate-wrappers.ts)
4. ✅ Executor HTTP API (executor.ts)
5. ✅ 63 tool wrappers generated
6. ✅ Health and tools endpoints
7. ✅ Documentation (README.md, CLAUDE.md)

**Testing:**
- ✅ Service deployment
- ✅ Simple code execution (console.log)
- ✅ Health endpoint
- ✅ Tool wrapper generation
- ✅ MCP tool calling (single tool - filesystem)
- ✅ Multi-tool workflows (timescaledb + minio)
- ✅ Discovery utilities (list servers and tools)

### ✅ Phase 2 Achievements (Core Features Complete)

**Progressive Disclosure API:**
- ✅ `/tools/search` endpoint with keyword and server filtering
- ✅ Three detail levels (name, description, full)
- ✅ `/tools/info/:server/:tool` for specific tool details
- ✅ Token estimation and metrics
- ⏸️ Token savings calculation (minor bug, non-blocking)

**Metrics & Monitoring:**
- ✅ Execution metrics (output bytes, token estimates)
- ✅ Performance tracking (execution time)
- ✅ Token usage comparison across detail levels

**Token Efficiency Demonstrated:**
- **Name-only**: 245 tokens for all 63 tools (97% savings)
- **With descriptions**: 1,181 tokens for all 63 tools (85% savings)
- **Full sources**: ~7,685 tokens (only when needed)

**API Endpoints Added:**
- `GET /tools/search` - Search with progressive disclosure
- `GET /tools/info/:server/:tool` - Get specific tool details
- Enhanced `POST /execute` - Now includes metrics

### ⏳ Phase 3 Planning (Future)

**Skills Framework:**
- [ ] Persistent storage for skills
- [ ] Skill creation API
- [ ] Pre-built skill library
- [ ] Progressive disclosure for skills

**Privacy & Security:**
- [ ] Data tokenization layer
- [ ] Sensitive field detection
- [ ] Data flow policies

**Integration:**
- [ ] Open WebUI integration
- [ ] Claude Code CLI integration
- [ ] LiteLLM routing

---

## Known Issues (RESOLVED)

### ~~Issue 1: Module Resolution~~ ✅ FIXED

**Problem:** Execution happens in `/tmp/executions` but tools are in `/workspace`
**Solution:** Changed wrapper generator to use absolute paths `/app/client.js`
**Status:** RESOLVED (2025-11-08)

### ~~Issue 2: Top-Level Await~~ ✅ FIXED

**Problem:** tsx defaults to CJS output, doesn't support top-level await
**Solution:** Implemented auto-wrapping logic that preserves imports outside async IIFE
**Status:** RESOLVED (2025-11-08)

### Issue 3: Tmpfs Permissions (WORKAROUND IN PLACE)

**Problem:** tmpfs mounted by Docker as root
**Workaround:** `docker exec -u root mcp-code-executor chown -R node:node /workspace /tmp/executions`
**Future Fix:** Configure tmpfs with proper uid/gid in docker-compose.yml
**Status:** Documented in deploy procedure

---

## Metrics (Phase 1)

**Tool Wrappers:**
- Generated: 63 tools
- Servers: 9
- Success Rate: 100%
- Generation Time: <10 seconds

**Performance:**
- Simple execution: ~555ms
- Health check: <100ms
- Container memory: ~150MB
- Workspace size: 0MB (tmpfs empty until first use)

**Token Savings (Estimated):**
- Before: 58 tools loaded upfront (~50,000 tokens)
- After: Load 1-3 tools on-demand (~2,000 tokens)
- **Projected Reduction: 96%+ for simple tasks**

---

## Architecture Decisions

### Why Tmpfs for Workspace?

**Decision**: Use tmpfs instead of bind mount for Phase 1
**Reason**: Permission issues with bind mount (UID mismatch)
**Trade-off**: No persistence between container restarts
**Future**: Phase 2 will add persistent volume for skills

### Why Fastify?

**Decision**: Fastify over Express
**Reason**: Native async/await, better performance, TypeScript support
**Performance**: ~3x faster than Express for API workloads

### Why TypeScript Wrappers?

**Decision**: Generate wrappers instead of dynamic calls
**Reason**: Type safety, IDE autocomplete, progressive disclosure
**Alternative**: Could call MCP proxy directly (simpler but less ergonomic)

---

## Files Structure

```
/home/administrator/projects/mcp/code-executor/
├── client.ts              # MCP HTTP client library
├── executor.ts            # Fastify HTTP API server
├── generate-wrappers.ts   # Tool wrapper generator
├── Dockerfile             # Container definition
├── docker-compose.yml     # Service configuration
├── package.json           # Node dependencies
├── tsconfig.json          # TypeScript config
├── deploy.sh              # Deployment script
├── README.md              # User documentation
├── CLAUDE.md              # This file (project context)
└── .dockerignore          # Build exclusions
```

---

## Production Validation ✅

### End-to-End Tests (All Passing)

1. **✅ Simple Execution**: Basic console.log (555ms)
2. **✅ Discovery**: List all 9 servers and 63 tools
3. **✅ Single MCP Tool**: filesystem.list_allowed_directories (663ms)
4. **✅ Multi-Tool Workflow**: timescaledb + minio in single execution (800ms)

### Deployment Verification

```bash
# Service Status
curl http://localhost:9091/health
# ✅ Status: healthy, 9 servers, 63 tools

# Tool Wrappers
docker exec mcp-code-executor ls -la /workspace/servers/
# ✅ 9 directories, 73 files (63 tools + 9 indexes + discovery.ts)

# Permissions
docker exec mcp-code-executor touch /workspace/test
# ✅ No permission errors
```

---

**Last Updated**: 2025-11-08
**Status**: ✅ **PRODUCTION READY**
**Next**: Phase 2 - Progressive Disclosure API & Integration

**Phase 1 Complete**: User requested to proceed with Phase 2 after Phase 1 is working and production-ready.
