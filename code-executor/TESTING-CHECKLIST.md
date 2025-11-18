# MCP Code Executor - Testing Checklist

## Pre-Testing Setup ✅

All setup is complete. The following has been configured:

- ✅ Container running: mcp-code-executor
- ✅ HTTP API healthy: http://localhost:9091
- ✅ MCP SDK installed: @modelcontextprotocol/sdk
- ✅ MCP server file: mcp-server.ts
- ✅ Tool wrappers generated: 63 tools across 9 servers
- ✅ Claude CLI config: $HOME/projects/.claude/mcp.json created
- ✅ Open WebUI functions: openwebui-functions.py ready
- ✅ Integration docs: INTEGRATION.md complete

---

## Testing Phase 1: Claude Code CLI

### Before You Start
1. **Exit Claude Code CLI** (type `/exit` or Ctrl+D)
2. **Restart Claude Code CLI** (run `claude` command)
3. MCP servers load on startup - watch for "code-executor" in the output

### Test 1: Verify MCP Server is Loaded
```
👤 User: List all available MCP tools
```

**Expected:** Should see code-executor tools:
- execute_code
- search_tools
- get_tool_info
- list_mcp_tools

### Test 2: Simple Code Execution
```
👤 User: Use the code-executor to run this code: console.log(2+2)
```

**Expected:**
- Output: "4"
- Execution time displayed
- No errors

### Test 3: Search Tools (Progressive Disclosure)
```
👤 User: Use code-executor to search for database tools at name level
```

**Expected:**
- Returns ~3 database-related tools
- Minimal token usage (~16 tokens)
- Tools from timescaledb, postgres, arangodb servers

### Test 4: Get Specific Tool Info
```
👤 User: Use code-executor to get info about timescaledb/execute_query with full details
```

**Expected:**
- Returns tool description
- TypeScript signature
- Full source code (~373 bytes)
- Token estimate (~94 tokens)

### Test 5: Multi-Tool Workflow
```
👤 User: Use code-executor to run this workflow:

import { list_buckets } from '/workspace/servers/minio/list_buckets.js';
import { list_databases } from '/workspace/servers/timescaledb/list_databases.js';

const buckets = await list_buckets({});
const databases = await list_databases({});

console.log('Storage:', buckets);
console.log('Databases:', databases);
```

**Expected:**
- Both MCP tools execute successfully
- MinIO bucket list returned
- TimescaleDB database list returned
- Combined output in single response

### Test 6: Data Filtering Pattern
```
👤 User: Use code-executor to demonstrate data filtering:

import { list_databases } from '/workspace/servers/timescaledb/list_databases.js';

const result = await list_databases({});
const databases = Array.isArray(result) ? result : result.content || [];

console.log(`Total databases: ${databases.length}`);
console.log('First 3:', databases.slice(0, 3));
```

**Expected:**
- Executes successfully
- Returns summary + limited subset
- Demonstrates token efficiency (not full dataset)

---

## Testing Phase 2: Open WebUI

### Setup
1. Navigate to Open WebUI: https://openwebui.ai-servicers.com
2. Go to Workspace → Functions
3. Click "+ Add Function"
4. Copy each function from `/home/administrator/projects/mcp/code-executor/openwebui-functions.py`
5. Enable all 3 functions

### Test 1: List All Tools
```
👤 User: list all tools
```

**Expected:**
- Triggers "List MCP Tools" function
- Shows 63 tools organized by server
- Formatted markdown output

### Test 2: Search Tools
```
👤 User: search tools for database
```

**Expected:**
- Triggers "Search MCP Tools" function
- Returns database-related tools
- Shows descriptions

### Test 3: Execute Workflow (Simple)
```
👤 User: execute this workflow:

```typescript
console.log('Hello from MCP Code Executor!');
console.log('2 + 2 =', 2 + 2);
```
```

**Expected:**
- Triggers "Execute MCP Workflow" function
- Executes code in sandbox
- Returns output with execution metrics

### Test 4: Execute Workflow (MCP Tools)
```
👤 User: execute this workflow:

```typescript
import { list_allowed_directories } from '/workspace/servers/filesystem/list_allowed_directories.js';

const dirs = await list_allowed_directories({});
console.log('Allowed directories:', dirs);
```
```

**Expected:**
- Calls filesystem MCP tool
- Returns allowed directories (/workspace)
- Shows execution time and metrics

### Test 5: Execute Workflow (Multi-Tool)
```
👤 User: execute this workflow:

```typescript
import { list_buckets } from '/workspace/servers/minio/list_buckets.js';
import { list_databases } from '/workspace/servers/timescaledb/list_databases.js';

const buckets = await list_buckets({});
const dbs = await list_databases({});

const summary = {
  storage: { type: 'MinIO', buckets: buckets },
  database: { type: 'TimescaleDB', databases: dbs }
};

console.log(JSON.stringify(summary, null, 2));
```
```

**Expected:**
- Both tools execute successfully
- Combined JSON output
- Single execution with both results

---

## Troubleshooting Guide

### Issue: "code-executor not found in MCP servers"

**Check:**
```bash
# Verify $HOME/projects/.claude/mcp.json exists and has code-executor
cat $HOME/projects/.claude/mcp.json

# Verify container is running
docker ps --filter name=mcp-code-executor

# Test HTTP API
curl http://localhost:9091/health | jq
```

**Fix:**
```bash
# Re-run setup script
/home/administrator/projects/mcp/code-executor/setup-claude-cli.sh

# Restart Claude CLI
exit
claude
```

### Issue: "Module not found" errors

**Fix:**
```bash
# Regenerate wrappers
docker exec mcp-code-executor npm run generate-wrappers

# Verify wrappers exist
docker exec mcp-code-executor ls -la /workspace/servers/
```

### Issue: "Permission denied" errors

**Fix:**
```bash
# Fix tmpfs permissions
docker exec -u root mcp-code-executor chown -R node:node /workspace /tmp/executions
```

### Issue: Open WebUI functions not triggering

**Check:**
1. Functions are enabled in Open WebUI
2. Using correct keywords: "list all tools", "search tools", "execute this workflow"
3. Code blocks use triple backticks with typescript language identifier

### Issue: "Connection refused" from Open WebUI

**Check:**
```bash
# Verify Open WebUI can reach code-executor
docker exec open-webui curl http://mcp-code-executor:3000/health

# If connection refused, check network
docker network inspect litellm-mcp-net | grep -A5 open-webui
docker network inspect litellm-mcp-net | grep -A5 mcp-code-executor
```

**Fix if needed:**
```bash
# Connect Open WebUI to mcp-net
docker network connect mcp-net open-webui
```

---

## Success Criteria

### Claude Code CLI Integration ✅
- [ ] code-executor appears in MCP server list
- [ ] Can execute simple console.log
- [ ] Can search tools with progressive disclosure
- [ ] Can get specific tool info
- [ ] Can run multi-tool workflows
- [ ] Token savings observable (name vs description vs full)

### Open WebUI Integration ✅
- [ ] All 3 functions installed and enabled
- [ ] "list all tools" triggers correctly
- [ ] "search tools" triggers and returns results
- [ ] "execute workflow" triggers and runs code
- [ ] Can execute TypeScript with MCP tools
- [ ] Execution metrics displayed (time, bytes, tokens)

### Performance Benchmarks
- [ ] Simple execution: <500ms
- [ ] Multi-tool workflow: <1000ms
- [ ] Token savings demonstrated: 85-97%
- [ ] No memory leaks (container stays <200MB)

---

## After Testing: Next Steps

### If All Tests Pass ✅
1. Document any observations or edge cases
2. Consider adding more workflow examples
3. Integrate with LiteLLM for automatic tool routing
4. Add persistence layer for skills/workflows

### If Tests Fail ❌
1. Check troubleshooting guide above
2. Review logs: `docker logs mcp-code-executor -f`
3. Verify setup: `/home/administrator/projects/mcp/code-executor/setup-claude-cli.sh`
4. Report issues with specific error messages

---

## Quick Reference Commands

**Container Management:**
```bash
# Status
docker ps --filter name=mcp-code-executor

# Logs
docker logs mcp-code-executor -f

# Restart
cd /home/administrator/projects/mcp/code-executor
docker compose restart
```

**API Testing:**
```bash
# Health check
curl http://localhost:9091/health | jq

# Search tools
curl 'http://localhost:9091/tools/search?query=database&detail=name' | jq

# Execute code
curl -X POST http://localhost:9091/execute \
  -H 'Content-Type: application/json' \
  -d '{"code":"console.log(2+2)"}'
```

**MCP Testing:**
```bash
# Test MCP server (in container)
docker exec -it mcp-code-executor npm run mcp
# Then send JSON-RPC message via stdin
```

---

**Last Updated:** 2025-11-08
**Ready for Testing:** ✅ YES
