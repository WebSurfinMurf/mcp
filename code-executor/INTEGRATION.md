# MCP Code Executor - Integration Guide

## Claude Code CLI Integration

### Quick Setup

1. **Install the MCP server in Claude Code:**

```bash
# Navigate to the code-executor directory
cd /home/administrator/projects/mcp/code-executor

# Rebuild container with MCP SDK
docker compose down
docker compose build
docker compose up -d

# Fix permissions and generate wrappers
docker exec -u root mcp-code-executor chown -R node:node /workspace /tmp/executions
docker exec mcp-code-executor npm run generate-wrappers

# Install MCP SDK in container
docker exec mcp-code-executor npm install
```

2. **Add to Claude Code MCP configuration:**

```bash
# Add the code-executor server to your Claude Code MCP config
cat >> $HOME/projects/.claude/mcp.json << 'EOF'
{
  "mcpServers": {
    "code-executor": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "mcp-code-executor",
        "npm",
        "run",
        "mcp"
      ],
      "env": {
        "CODE_EXECUTOR_URL": "http://localhost:9091"
      }
    }
  }
}
EOF
```

Or manually merge the content from `claude-mcp-config.json`.

3. **Verify installation:**

Exit and restart Claude Code CLI, then verify the code-executor tools are available.

---

## Available Tools in Claude Code

Once integrated, you'll have 4 new tools:

### 1. `execute_code`
Execute TypeScript/JavaScript with access to all 63 MCP tools.

**Use Cases:**
- Multi-tool workflows (query DB → filter → upload to S3)
- Complex data processing (filter large datasets before returning)
- Control flow (loops, conditionals, error handling)

**Example:**
```typescript
import { execute_query } from '/workspace/servers/timescaledb/execute_query.js';
import { upload_object } from '/workspace/servers/minio/upload_object.js';

const result = await execute_query({
  query: "SELECT * FROM metrics WHERE value > 100"
});

const csv = result.rows.map(r => Object.values(r).join(',')).join('\n');
await upload_object({
  bucket: 'exports',
  key: 'critical-metrics.csv',
  content: csv
});

console.log(`Exported ${result.rowCount} rows`);
```

### 2. `search_tools`
Search available MCP tools with progressive disclosure.

**Parameters:**
- `query`: Search keyword (optional)
- `server`: Filter by server (optional)
- `detail`: Level of detail - "name" | "description" | "full"

**Token Savings:**
- `detail="name"`: 97% savings (245 tokens for all 63 tools)
- `detail="description"`: 85% savings (1,181 tokens)
- `detail="full"`: 0% savings (7,685 tokens)

### 3. `get_tool_info`
Get detailed information about a specific tool.

**Parameters:**
- `server`: MCP server name (required)
- `tool`: Tool name (required)
- `detail`: "name" | "description" | "full"

### 4. `list_mcp_tools`
List all 63 available tools organized by server.

---

## Open WebUI Integration

### Option 1: Via MCP Middleware (Recommended)

The code-executor is already accessible via the existing MCP middleware at `http://localhost:4001`.

**Status:** Not yet integrated into middleware
**Action Required:** Add code-executor endpoints to `projects/mcp/middleware/main.py`

### Option 2: Direct HTTP API

Open WebUI can call the code-executor HTTP API directly via custom functions.

**Endpoint:** `http://mcp-code-executor:3000` (internal Docker network)

**Example Function:**
```python
# Open WebUI Custom Function
import requests

def execute_workflow(code: str) -> str:
    """Execute a TypeScript workflow with access to MCP tools"""
    response = requests.post(
        'http://mcp-code-executor:3000/execute',
        json={'code': code}
    )
    result = response.json()

    if result.get('error'):
        return f"Error: {result['error']}"

    return f"{result['output']}\n\nExecution: {result['executionTime']}ms"
```

### Option 3: New Model in LiteLLM

Add code-executor as a tool-augmented model variant.

**Status:** Future implementation
**Benefit:** Automatic tool injection and execution loop

---

## Testing the Integration

### Test 1: Simple Execution (Claude Code CLI)

After setup, in Claude Code CLI:
```
User: Use the code-executor to run: console.log(2+2)
```

Expected: Claude calls `execute_code` tool and returns output "4".

### Test 2: Multi-Tool Workflow

```
User: Use code-executor to list all MinIO buckets and TimescaleDB databases, then create a summary
```

Expected: Claude writes code importing both tools, executes, returns formatted summary.

### Test 3: Progressive Disclosure

```
User: Search for database-related tools at name level
```

Expected: Claude calls `search_tools` with query="database" and detail="name", returns 3 tools with minimal tokens.

---

## Token Efficiency Comparison

### Before (Direct MCP Tool Calls)
- Load 63 tool schemas upfront: ~7,685 tokens
- Each tool call: Individual request/response
- Total for 3-tool workflow: ~8,000+ tokens

### After (Code Executor)
- Discovery: 245 tokens (name-only) or 1,181 tokens (with descriptions)
- Execute workflow: Single request with all 3 tools
- Return only final output
- **Total: ~1,500 tokens (80% reduction)**

---

## Workflow Examples

### Example 1: Data Filtering
```typescript
// Instead of returning 10,000 rows to Claude...
import { execute_query } from '/workspace/servers/timescaledb/execute_query.js';

const result = await execute_query({
  query: "SELECT * FROM logs WHERE timestamp > NOW() - INTERVAL '1 day'"
});

// Filter in executor (not in Claude's context!)
const errors = result.rows.filter(r => r.level === 'ERROR');

// Return only summary
console.log(`Found ${errors.length} errors out of ${result.rowCount} total logs`);
console.log('First 5 errors:', errors.slice(0, 5));
```

**Token Savings:** 95%+ (10K rows → 5 error summaries)

### Example 2: Multi-Step Pipeline
```typescript
// Read config → Query DB → Upload to S3 (all in one execution)
import { read_file } from '/workspace/servers/filesystem/read_file.js';
import { execute_query } from '/workspace/servers/postgres/query.js';
import { upload_object } from '/workspace/servers/minio/upload_object.js';

const config = JSON.parse(await read_file({ path: '/workspace/query-config.json' }));
const result = await execute_query({ sql: config.query });
const csv = result.rows.map(r => Object.values(r).join(',')).join('\n');

await upload_object({
  bucket: 'exports',
  key: `export-${Date.now()}.csv`,
  content: csv
});

console.log(`Exported ${result.rows.length} rows to MinIO`);
```

**Token Savings:** 90%+ (3 separate tool calls → 1 execution with summary)

### Example 3: Error Handling
```typescript
// Retry logic without exposing failures to Claude
import { execute_query } from '/workspace/servers/timescaledb/execute_query.js';

let attempt = 0;
const maxRetries = 3;
let result;

while (attempt < maxRetries) {
  try {
    result = await execute_query({ query: "SELECT NOW()" });
    break;
  } catch (error) {
    attempt++;
    if (attempt >= maxRetries) throw error;
    await new Promise(r => setTimeout(r, 1000));
  }
}

console.log(`Success after ${attempt + 1} attempt(s)`);
```

**Token Savings:** Hides retry attempts from Claude's context

---

## Troubleshooting

### "MCP server not responding"
```bash
# Check container is running
docker ps --filter name=mcp-code-executor

# Check API is healthy
curl http://localhost:9091/health

# Rebuild if needed
cd /home/administrator/projects/mcp/code-executor
docker compose down && docker compose build && docker compose up -d
docker exec -u root mcp-code-executor chown -R node:node /workspace /tmp/executions
docker exec mcp-code-executor npm install
docker exec mcp-code-executor npm run generate-wrappers
```

### "Module not found" errors
```bash
# Regenerate tool wrappers
docker exec mcp-code-executor npm run generate-wrappers

# Verify wrappers exist
docker exec mcp-code-executor ls -la /workspace/servers/
```

### "Permission denied" errors
```bash
# Fix tmpfs permissions
docker exec -u root mcp-code-executor chown -R node:node /workspace /tmp/executions
```

---

## Next Steps

1. ✅ Test Claude Code CLI integration (restart session and test)
2. ⏳ Add to MCP middleware for Open WebUI
3. ⏳ Create Open WebUI custom functions
4. ⏳ Document production deployment patterns

---

**Last Updated:** 2025-11-08
**Status:** Ready for testing
