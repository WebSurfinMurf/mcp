# LiteLLM Smart Router MCP Integration Error

**Date**: 2025-09-17
**Status**: ❌ **Smart Router Approach Failed - Protocol Mismatch**

## Current State Summary

### ✅ What's Working
1. **PostgreSQL MCP Server**: Fully operational at `http://mcp-postgresql:8080`
   - **18 tools available**: All PostgreSQL tools discoverable and functional
   - **Direct tool execution**: Works perfectly via HTTP API
   - **Docker networking**: LiteLLM container can reach MCP server via `mcp-postgresql:8080`
   - **Health status**: Healthy and responding correctly

2. **LiteLLM Configuration**: Clean startup without errors
   - **21 models total**: 17 AI models + 4 PostgreSQL "models"
   - **No mcp_servers dependency**: Removed as requested by user
   - **Smart Router format**: Correctly formatted using `openai/` provider prefix

3. **Tool Discovery**: MCP server properly exposes tool schemas
   ```bash
   curl -s http://linuxserver.lan:8080/tools
   # Returns: 18 PostgreSQL tools with full JSON schemas
   ```

4. **Direct Tool Execution**: Works perfectly
   ```bash
   curl -s -X POST http://linuxserver.lan:8080/tools/pg_execute_query \
     -H "Content-Type: application/json" \
     -d '{"arguments": {"operation": "select", "query": "SELECT datname FROM pg_database WHERE datistemplate = false;"}}'
   # Returns: 12 databases successfully
   ```

### ❌ What's Not Working

**Smart Router Integration**: Complete protocol mismatch between LiteLLM and MCP tools

## The Core Problem: Protocol Mismatch

### LiteLLM Expectation (OpenAI Chat Completions)
```http
POST /tools/pg_execute_query/chat/completions
Content-Type: application/json
Authorization: Bearer sk-xxx

{
  "model": "pg_execute_query",
  "messages": [{"role": "user", "content": "..."}]
}
```

### MCP Server Reality (Direct Tool Execution)
```http
POST /tools/pg_execute_query
Content-Type: application/json

{
  "arguments": {
    "operation": "select",
    "query": "SELECT ..."
  }
}
```

## Error Details

### LiteLLM Smart Router Error
```
litellm.NotFoundError: NotFoundError: OpenAIException -
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Error</title></head>
<body><pre>Cannot POST /tools/pg_execute_query/chat/completions</pre></body>
</html>

Received Model Group=pg_execute_query
Available Model Group Fallbacks=None
```

**Root Cause**: LiteLLM automatically appends `/chat/completions` to the `api_base` URL, expecting an OpenAI-compatible endpoint.

## Configuration Attempted

### Smart Router Config (FAILED)
```yaml
model_list:
  - model_name: pg_execute_query
    litellm_params:
      model: openai/pg_execute_query
      api_base: "http://mcp-postgresql:8080/tools/pg_execute_query"
      api_key: "dummy-key"
```

**Result**: LiteLLM calls `http://mcp-postgresql:8080/tools/pg_execute_query/chat/completions` which doesn't exist.

## Alternative Solutions

### 1. Manual Tool Registration (WORKING)
Include tools manually in each LLM conversation:
```bash
curl -s https://litellm.ai-servicers.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-xxx" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "List databases"}],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "pg_execute_query",
          "description": "Execute SELECT queries",
          "parameters": { ... }
        }
      }
    ]
  }'
```

### 2. Direct MCP Server Usage (WORKING)
Bypass LiteLLM entirely for tool execution:
```bash
# Step 1: Get AI response with tool calls
curl https://litellm.ai-servicers.com/v1/chat/completions

# Step 2: Execute tools directly on MCP server
curl -X POST http://linuxserver.lan:8080/tools/pg_execute_query

# Step 3: Return results to AI conversation
```

### 3. Create OpenAI-Compatible Wrapper (POTENTIAL SOLUTION)
Build a middleware that:
- Accepts OpenAI `/chat/completions` requests
- Extracts tool calls from messages
- Executes tools on MCP server
- Returns results in OpenAI format

### 4. Use LiteLLM Native MCP Support (REJECTED BY USER)
```yaml
mcp_servers:
  postgresql_mcp:
    transport: "http"
    endpoint: "http://mcp-postgresql:8080"
```
**Status**: User explicitly requested no `mcp_servers` dependency.

## Technical Analysis

### Why Smart Router Fails
1. **LiteLLM is designed for LLM routing**, not tool routing
2. **OpenAI Chat Completions API** expects conversational model interfaces
3. **MCP Protocol** uses direct tool execution with JSON arguments
4. **URL path mismatch**: `/chat/completions` vs `/tools/{name}`
5. **Request format mismatch**: Messages vs Arguments

### MCP Server Architecture
```
PostgreSQL MCP Server (http-adapter.js)
├── /health (GET) - Health check
├── /tools (GET) - List all tools
└── /tools/{toolName} (POST) - Execute specific tool
    └── Body: {"arguments": {...}}
```

### LiteLLM Router Architecture
```
LiteLLM Smart Router
├── Routes to model endpoints expecting /chat/completions
├── Appends /chat/completions to api_base automatically
└── Expects OpenAI-compatible JSON response format
```

## Conclusion

**Smart Router approach is fundamentally incompatible** with MCP tool execution due to protocol differences. The MCP server is working perfectly - the issue is architectural mismatch between:

- **LiteLLM**: Designed for model routing with OpenAI Chat Completions API
- **MCP Protocol**: Designed for direct tool execution with JSON-RPC-style calls

## Working Solution

**Use direct MCP server integration** without trying to route through LiteLLM's model system:

1. **AI Planning**: Use LiteLLM for AI model responses
2. **Tool Execution**: Call MCP server directly for PostgreSQL operations
3. **Result Integration**: Combine AI responses with tool results

This approach provides:
- ✅ Full access to 18 PostgreSQL tools
- ✅ No dependency on LiteLLM's `mcp_servers`
- ✅ Clean separation of concerns
- ✅ Maximum flexibility and performance

## Files Modified

- `/home/administrator/projects/litellm/config.yaml` - Smart Router configuration (failed)
- `/home/administrator/projects/mcp/pilot/postgresql/` - MCP server (working)
- Docker network connectivity established between `litellm` and `mcp-postgresql` containers

## Next Steps

1. **Document the working direct MCP approach**
2. **Create middleware if needed for tool auto-injection**
3. **Implement filesystem and monitoring MCP servers using same pattern**
4. **Consider building OpenAI-compatible wrapper if automatic routing is required**