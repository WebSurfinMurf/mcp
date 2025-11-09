# MCP Code Executor

**Sandboxed TypeScript/Python execution environment for MCP tools with progressive disclosure**

## Overview

The MCP Code Executor enables AI agents to write and execute code that calls MCP tools, implementing the progressive disclosure pattern described in Anthropic's [Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp) article.

### Key Benefits

- **98.7% Token Reduction**: Load only needed tool definitions instead of all 58 tools upfront
- **Context Efficiency**: Filter/transform large datasets in execution environment
- **Powerful Control Flow**: Loops, conditionals, error handling in code
- **State Persistence**: Save code as reusable skills
- **Privacy-Preserving**: Data flows through workflow without entering model context

## Architecture

```
AI Agent
    ↓ (writes TypeScript code)
Executor API (port 3000)
    ↓ (executes in sandbox)
MCP Client Library
    ↓ (HTTP requests)
MCP Proxy (port 9090)
    ↓ (stdio/SSE)
MCP Servers (58 tools)
```

## Quick Start

### 1. Deploy Service

```bash
cd /home/administrator/projects/mcp/code-executor
./deploy.sh
```

### 2. Generate Tool Wrappers

```bash
docker exec mcp-code-executor npm run generate-wrappers
```

This creates TypeScript wrappers for all 58 MCP tools in `/workspace/servers/`:

```
/workspace/servers/
├── filesystem/
│   ├── read_file.ts
│   ├── write_file.ts
│   ├── list_directory.ts
│   └── index.ts
├── postgres/
│   └── execute_sql.ts
├── timescaledb/
│   ├── execute_query.ts
│   └── list_databases.ts
└── ... (9 servers total)
```

### 3. Execute Code

```bash
curl -X POST http://localhost:3000/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "import { read_file } from \"./servers/filesystem/read_file.js\";\nconst content = await read_file({ path: \"/workspace/test.txt\" });\nconsole.log(content);",
    "timeout": 60000
  }'
```

## API Reference

### POST /execute

Execute TypeScript or Python code in sandboxed environment.

**Request:**
```json
{
  "code": "console.log('Hello World')",
  "timeout": 60000,
  "language": "typescript"
}
```

**Response:**
```json
{
  "output": "Hello World\n",
  "executionTime": 123,
  "truncated": false
}
```

**Error Response:**
```json
{
  "output": "",
  "error": "Execution timed out after 60000ms",
  "executionTime": 60001
}
```

### GET /health

Health check and service status.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 12345,
  "servers": 9,
  "totalTools": 58,
  "toolsByServer": {
    "filesystem": ["read_file", "write_file", ...],
    "postgres": ["execute_sql"],
    ...
  }
}
```

### GET /tools

List all available tool wrappers.

**Response:**
```json
{
  "servers": 9,
  "totalTools": 58,
  "tools": {
    "filesystem": ["read_file", "write_file", ...],
    ...
  }
}
```

## Usage Patterns

### Pattern 1: Progressive Disclosure

**Before (Direct Tool Calling):**
- Agent sees all 58 tool definitions (~50,000 tokens)
- Calls 1 tool
- Total: ~50,000 tokens

**After (Code Execution):**
- Agent lists `/workspace/servers/` (discovers 9 servers)
- Reads `/workspace/servers/filesystem/read_file.ts` (1 tool definition)
- Writes code to call it
- Total: ~2,000 tokens (97% reduction)

### Pattern 2: Data Filtering

**Before:**
```typescript
// All 10,000 rows in context
const result = await timescaledb_execute_query({
  query: "SELECT * FROM metrics WHERE timestamp > NOW() - INTERVAL '1 day'"
});
// Model manually filters to 10 critical rows
```

**After:**
```typescript
// Code executes in sandbox
import { execute_query } from './servers/timescaledb/execute_query.js';

const result = await execute_query({
  query: "SELECT * FROM metrics WHERE timestamp > NOW() - INTERVAL '1 day'"
});

// Filter in execution environment
const critical = result.rows.filter(m => m.value > 100);

// Only 10 rows returned to model
console.log(JSON.stringify(critical.slice(0, 10)));
```

### Pattern 3: Multi-Tool Composition

```typescript
// Read file → Query DB → Upload result
// All without intermediate results in model context

import { read_file } from './servers/filesystem/read_file.js';
import { execute_sql } from './servers/postgres/execute_sql.js';
import { upload_object } from './servers/minio/upload_object.js';

// Read config
const config = JSON.parse(await read_file({ path: '/workspace/config.json' }));

// Query database
const result = await execute_sql({ sql: config.query });

// Transform to CSV
const csv = result.rows.map(r => Object.values(r).join(',')).join('\n');

// Upload to S3
await upload_object({
  bucket: 'exports',
  key: `export-${Date.now()}.csv`,
  content: csv
});

console.log(`Exported ${result.rows.length} rows`);
```

## Security

### Sandbox Restrictions

- **User**: Non-root (UID 1000)
- **Filesystem**: Read-only root, write-only `/tmp/executions` (100MB, noexec)
- **Network**: Only `mcp-net` (no internet access)
- **Resources**: 1 CPU core, 1GB RAM
- **Timeout**: 5 minutes max
- **Output**: 100KB max
- **Privileges**: `no-new-privileges:true`

### What Can Execute

✅ **Allowed:**
- TypeScript/JavaScript (via `tsx`)
- Python 3
- MCP tool calls via wrappers
- File operations in `/workspace`
- Temp files in `/tmp/executions`

❌ **Blocked:**
- Internet access
- Docker commands
- System commands (except in `/tmp`)
- Binary execution from `/tmp` (noexec)
- Privilege escalation

## Tool Wrapper Structure

Each tool gets a TypeScript wrapper:

```typescript
// /workspace/servers/filesystem/read_file.ts

import { callMCPTool } from '../../../client.js';

export type ReadFileInput = {
  path: string;
};

export type ReadFileResponse = any;

/** Read the complete contents of a file from the file system */
export async function read_file(input: ReadFileInput): Promise<ReadFileResponse> {
  return callMCPTool<ReadFileResponse>('filesystem', 'read_file', input);
}
```

## Development

### Build Container

```bash
docker compose build
```

### Run Locally

```bash
npm install
tsx executor.ts
```

### Generate Wrappers Manually

```bash
tsx generate-wrappers.ts
```

### Test Execution

```bash
# TypeScript
curl -X POST http://localhost:3000/execute \
  -H 'Content-Type: application/json' \
  -d '{"code":"console.log(2+2)"}'

# Python
curl -X POST http://localhost:3000/execute \
  -H 'Content-Type: application/json' \
  -d '{"code":"print(2+2)","language":"python"}'
```

## Monitoring

### Logs

```bash
docker logs mcp-code-executor -f
```

### Health

```bash
curl http://localhost:3000/health | jq
```

### Resource Usage

```bash
docker stats mcp-code-executor
```

## Troubleshooting

### Issue: No tools generated

**Cause**: MCP proxy not accessible

**Solution**:
```bash
docker exec mcp-code-executor curl http://mcp-proxy:9090/filesystem/mcp
```

### Issue: Execution timeout

**Cause**: Code running too long or infinite loop

**Solution**: Reduce timeout or fix code logic

### Issue: Output truncated

**Cause**: Output exceeds 100KB limit

**Solution**: Filter/summarize output in code

## Future Enhancements

- [ ] Python MCP client library
- [ ] Skill persistence framework (`/workspace/skills/`)
- [ ] Data tokenization layer
- [ ] Progressive disclosure search API
- [ ] Execution metrics and dashboards
- [ ] Skills library (reusable code snippets)

## References

- [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Cloudflare Code Mode](https://blog.cloudflare.com/code-mode/)
- [Model Context Protocol](https://modelcontextprotocol.io/)

---

**Version**: 1.0.0
**Status**: Phase 1 Complete
**Last Updated**: 2025-11-08
