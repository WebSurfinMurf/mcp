# LiteLLM MCP Integration Issue - Function Calls Not Executing

**Date:** 2025-09-21
**Status:** Partially Working - Function calls generated but not executed
**Issue:** MCP tool functions are called by Claude but not executed by LiteLLM proxy

## Current State

### ✅ What's Working
1. **Database Connection**: LiteLLM connects to PostgreSQL successfully
2. **Environment Variables**: Proper substitution using `os.environ/VARIABLE_NAME` syntax
3. **Claude Model**: Healthy and responding (claude-3-haiku-20240307)
4. **Function Call Generation**: Claude correctly generates `tool_calls` with proper function names
5. **MCP Service**: mcp-postgres container running and receiving requests
6. **Network Connectivity**: All containers can communicate on shared networks

### ❌ What's NOT Working
1. **Function Execution**: Tool calls stop at `"finish_reason":"tool_calls"`
2. **Result Return**: No function results returned to client
3. **Complete MCP Flow**: Missing execution and response phase

## Configuration

### LiteLLM Config (`/home/administrator/projects/litellm/config/config.yaml`)
```yaml
litellm_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/DATABASE_URL
  json_logs: true
  detailed_debug: true
  mcp_aliases:
    db: db_main
    fs: filesystem_main

model_list:
  - model_name: claude-3-haiku-orchestrator
    litellm_params:
      model: claude-3-haiku-20240307
      api_key: os.environ/ANTHROPIC_API_KEY

virtual_keys:
  - api_key: os.environ/LITELLM_VIRTUAL_KEY_TEST
    models: ["gpt-4o-mock", "claude-3-haiku-orchestrator"]
    mcp_servers: ["db_main"]
    description: "Test key for local network access with MCP"

mcp_servers:
  db_main:
    transport: sse
    url: http://mcp-postgres:8080/sse
    api_keys:
      - os.environ/LITELLM_VIRTUAL_KEY_TEST
    description: "PostgreSQL database tools via SSE"
    timeout: 30
```

### Environment Variables (`/home/administrator/secrets/litellm.env`)
- ✅ LITELLM_MASTER_KEY: Properly set
- ✅ ANTHROPIC_API_KEY: Valid and working
- ✅ DATABASE_URL: PostgreSQL connection working
- ✅ LITELLM_VIRTUAL_KEY_TEST: Defined but not working in practice

## Test Results

### Function Call Test
```bash
curl -H "Authorization: Bearer sk-litellm-cecca390f610603ff5180ba0ba2674afc8f7689716daf25343de027d10c32404" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "claude-3-haiku-orchestrator",
       "messages": [{"role": "user", "content": "Use postgres_list_databases to show databases"}],
       "tools": [{"type": "function", "function": {"name": "postgres_list_databases", "description": "List PostgreSQL databases", "parameters": {"type": "object", "properties": {}}}}],
       "tool_choice": "auto"
     }' \
     http://localhost:4000/chat/completions
```

**Result:**
```json
{
  "choices": [{
    "finish_reason": "tool_calls",
    "message": {
      "role": "assistant",
      "tool_calls": [{
        "function": {
          "arguments": "{\"properties\": {}}",
          "name": "postgres_list_databases"
        },
        "id": "toolu_01FwQ69GkaYQfo2Ah76ggEjv",
        "type": "function"
      }]
    }
  }]
}
```

**Expected:** Follow-up execution with function results returned

## Research Findings

Based on research into LiteLLM MCP issues, common problems include:

### 1. **Finish Reason Problems**
- `finish_reason: "tool_calls"` indicates function call generated but not executed
- Should continue to execution phase and return `finish_reason: "stop"` with results
- Issue documented in GitHub issues for various LiteLLM integrations

### 2. **MCP Configuration Issues**
- Virtual keys may not be properly associated with MCP servers
- SSE transport may have connection/execution issues
- `require_approval: "never"` setting may be needed for automatic execution

### 3. **Known LiteLLM MCP Bugs**
- GitHub issue #16688: "MCP tool call parsed, but sometimes not executed"
- Discussion #7639: "MCP tools not called when using litellm and ollama"
- Various reports of incomplete tool execution flows

## Diagnostic Information

### MCP Postgres Service Status
```bash
$ docker logs mcp-postgres --tail 5
INFO:     172.31.0.3:37918 - "POST /messages/?session_id=b00421faa6864a9c94e8776364cf1040 HTTP/1.1" 202 Accepted
[09/21/25 22:36:59] INFO     Processing request of type ListToolsRequest
```
- Service receiving requests but no function execution logs

### LiteLLM Health Check
```bash
$ curl -H "Authorization: Bearer [MASTER_KEY]" http://localhost:4000/health
{
  "healthy_endpoints": [{"model": "claude-3-haiku-20240307", ...}],
  "unhealthy_endpoints": []
}
```
- Model healthy, no authentication issues

### Network Connectivity
```bash
$ docker exec litellm ping -c 1 mcp-postgres
PING mcp-postgres (172.31.0.2): 56 data bytes
64 bytes from 172.31.0.2: seq=0 ttl=64 time=0.077 ms
```
- Network connectivity confirmed working

## Potential Solutions to Try

### 1. **Check MCP Server Registration**
- Verify MCP servers are properly registered in LiteLLM database
- Check if virtual keys are correctly associated with MCP servers
- Test with master key instead of virtual key

### 2. **Add MCP Configuration Options**
```yaml
mcp_servers:
  db_main:
    transport: sse
    url: http://mcp-postgres:8080/sse
    api_keys: [os.environ/LITELLM_VIRTUAL_KEY_TEST]
    require_approval: "never"  # Auto-execute tools
    description: "PostgreSQL database tools via SSE"
    timeout: 30
```

### 3. **Test Direct MCP Connection**
- Test SSE endpoint directly: `curl -H "Accept: text/event-stream" http://mcp-postgres:8080/sse`
- Verify MCP postgres service can execute functions independently
- Check MCP tool definitions and schemas

### 4. **LiteLLM Debugging**
- Enable more detailed logging in LiteLLM
- Check if MCP tools are properly loaded at startup
- Verify function calling flow in LiteLLM logs

### 5. **Alternative Approaches**
- Test with different MCP transport (HTTP instead of SSE)
- Try different LiteLLM version or configuration format
- Use direct MCP client instead of LiteLLM proxy

## Commands for Next Steps

### Test MCP Direct Connection
```bash
# Test SSE endpoint
curl -H "Accept: text/event-stream" http://mcp-postgres:8080/sse

# Check MCP service directly
docker exec mcp-postgres python -m pytest tests/ || echo "No tests configured"

# Check LiteLLM MCP tool registration
curl -H "Authorization: Bearer [MASTER_KEY]" \
     -H "Accept: text/event-stream" \
     http://localhost:4000/mcp/servers/db_main/tools
```

### Debug LiteLLM MCP Integration
```bash
# Check database for MCP server registration
docker exec -e PGPASSWORD='LiteLLMPass2025' postgres \
    psql -U litellm_user -d litellm_db \
    -c "SELECT * FROM \"LiteLLM_MCPServers\";"

# Enable debug logging
docker logs litellm --tail 50 | grep -i "mcp\|tool\|function"
```

### Alternative Testing
```bash
# Test with master key instead of virtual key
curl -H "Authorization: Bearer sk-litellm-cecca390f610603ff5180ba0ba2674afc8f7689716daf25343de027d10c32404" \
     -H "Content-Type: application/json" \
     -d '{"model": "claude-3-haiku-orchestrator", "messages": [...]}' \
     http://localhost:4000/chat/completions

# Test function calling without MCP
curl -H "Authorization: Bearer sk-litellm-cecca390f610603ff5180ba0ba2674afc8f7689716daf25343de027d10c32404" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "claude-3-haiku-orchestrator",
       "messages": [{"role": "user", "content": "What is 2+2?"}],
       "tools": [{"type": "function", "function": {"name": "calculator", "description": "Simple calculator", "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}}}}]
     }' \
     http://localhost:4000/chat/completions
```

## Files and Locations

- **Config**: `/home/administrator/projects/litellm/config/config.yaml`
- **Secrets**: `/home/administrator/secrets/litellm.env`
- **Docker Compose**: `/home/administrator/projects/litellm/docker-compose.yml`
- **MCP Service**: Container `mcp-postgres` on networks `postgres-net`, `litellm-mcp-net`
- **LiteLLM Service**: Container `litellm` on port 4000

## Priority Issues

1. **Function execution not completing** - Tool calls generated but not executed
2. **Virtual key authentication failing** - May be related to MCP server association
3. **SSE transport verification** - Ensure proper MCP communication
4. **LiteLLM MCP integration bugs** - May need workarounds or alternative approaches

## Attempted Fix #1: require_approval: "never" (FAILED)

**Date Tested:** 2025-09-21 22:46

**What Was Tried:**
Added `require_approval: "never"` to the MCP server configuration:
```yaml
mcp_servers:
  db_main:
    transport: sse
    url: http://mcp-postgres:8080/sse
    api_keys:
      - os.environ/LITELLM_VIRTUAL_KEY_TEST
    description: "PostgreSQL database tools via SSE"
    timeout: 30
    require_approval: "never"  # <-- ADDED THIS
```

**Result:** Still same issue - `"finish_reason":"tool_calls"` but no execution

**Test Command:**
```bash
curl -H "Authorization: Bearer sk-litellm-cecca390f610603ff5180ba0ba2674afc8f7689716daf25343de027d10c32404" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "claude-3-haiku-orchestrator",
       "messages": [{"role": "user", "content": "Please use the postgres_list_databases function to show me all databases"}],
       "tools": [{"type": "function", "function": {"name": "postgres_list_databases", "description": "List all PostgreSQL databases", "parameters": {"type": "object", "properties": {}}}}],
       "tool_choice": "auto",
       "max_tokens": 1000
     }' \
     http://localhost:4000/chat/completions
```

**Response:** Function call generated but not executed

## Additional Discovery: Virtual Key Issue

**Problem Found:** Virtual keys are not being properly loaded from config
- Virtual key `sk-litellm-test-9768ce8475df0a3c5aa0d2f52571505b2ef09f3a21ec1af73859749fff4bb7cd` returns authentication error
- Database contains different token hashes than what's being sent
- This could be the root cause - MCP servers are associated with virtual keys that don't work

**Database Check:**
```bash
$ docker exec -e PGPASSWORD='LiteLLMPass2025' postgres psql -U litellm_user -d litellm_db -c "SELECT token, key_alias, models FROM \"LiteLLM_VerificationToken\" LIMIT 5;"
                              token                               | key_alias | models
------------------------------------------------------------------+-----------+--------
 7c30ba29b1788fb93cf3a88a224244f7e185cc85a0794e22a0638d2b750ed657 |           | {}
 48628a1bbb172ee26f37c661e696ac531f815248e8cfe719e7d17671f9fa6553 |           | {}
```

Token hashes in database don't match the virtual key being sent.

## Root Cause Analysis

**Primary Issue:** Virtual key authentication failing means MCP servers can't be accessed
- MCP servers are configured to only work with virtual keys (`api_keys: [os.environ/LITELLM_VIRTUAL_KEY_TEST]`)
- Virtual keys aren't properly loaded/hashed in the database
- Master key works for basic Claude calls but doesn't have MCP server access
- Function calls are generated by Claude but LiteLLM can't execute them because of authentication failure

## FINAL STATUS UPDATE (2025-09-21)

### ✅ RESOLVED ISSUES:
1. **Environment Variable Substitution** - FIXED
   - **Solution**: Use `os.environ/VARIABLE_NAME` instead of `${VARIABLE_NAME}` in LiteLLM config
   - **Applied to**: All config sections (master_key, database_url, api_keys, etc.)
   - **Status**: Working correctly

2. **Database Authentication** - FIXED
   - **Solution**: PostgreSQL SCRAM-SHA-256 password encryption
   - **Commands**: `SET password_encryption = 'scram-sha-256'; ALTER USER litellm_user PASSWORD 'LiteLLMPass2025';`
   - **Status**: Database connectivity working

3. **Virtual Key Authentication** - FIXED
   - **Solution**: Manually restored virtual key with correct SHA256 hash after database recreation
   - **Hash**: `d1fc78fe0a825d4d19685e9ec9f445cb8c584353e2d4838e202e80947738d763`
   - **Status**: Virtual key authentication working

4. **Model Configuration** - WORKING
   - **Model**: claude-3-haiku-20240307 healthy and responding
   - **API**: OpenAI-compatible endpoints functional
   - **Status**: All model operations working

### ❌ UNRESOLVED CRITICAL ISSUE:
**MCP Function Execution Failure**
- **Problem**: Function calls generated but not executed by LiteLLM
- **Symptoms**: Calls stop at `"finish_reason":"tool_calls"` without execution
- **Root Cause**: Unknown - appears to be LiteLLM MCP integration bug
- **Evidence**: GitHub issue #16688: "MCP tool call parsed, but sometimes not executed"

### 🔧 WORKING CONFIGURATION:
```yaml
litellm_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/DATABASE_URL

model_list:
  - model_name: claude-3-haiku-orchestrator
    litellm_params:
      model: claude-3-haiku-20240307
      api_key: os.environ/ANTHROPIC_API_KEY

virtual_keys:
  - api_key: os.environ/LITELLM_VIRTUAL_KEY_TEST
    models: ["claude-3-haiku-orchestrator"]
    mcp_servers: ["db_main"]

mcp_servers:
  db_main:
    transport: sse
    url: http://mcp-postgres:8080/sse
    api_keys: [os.environ/LITELLM_VIRTUAL_KEY_TEST]
    require_approval: "never"
```

### 🎯 REMAINING INVESTIGATION AREAS:

1. **LiteLLM MCP Execution Architecture**
   - How LiteLLM routes function calls to MCP servers after generation
   - Database associations required between virtual keys and MCP servers
   - Execution trigger mechanism for tool_calls → execution → results

2. **Database Schema Analysis**
   - Verify all MCP-related database tables are populated correctly
   - Check relationships between `LiteLLM_VerificationToken` and `LiteLLM_MCPServerTable`
   - Investigate if config-based MCP servers auto-populate database on startup

3. **Alternative Authentication Methods**
   - Test MCP servers with master key instead of virtual key
   - Try different virtual key configurations
   - Investigate if MCP server registration in database is required vs config-only

4. **LiteLLM Version/Bug Investigation**
   - Research known MCP execution issues in v1.77.3+
   - Test with different LiteLLM versions
   - Check for workarounds or patches for MCP execution bugs

### 📋 COMPREHENSIVE DEBUGGING COMMANDS:

```bash
# Database verification
docker exec -e PGPASSWORD='LiteLLMPass2025' postgres psql -U litellm_user -d litellm_db -c "SELECT token, key_alias, models FROM \"LiteLLM_VerificationToken\";"
docker exec -e PGPASSWORD='LiteLLMPass2025' postgres psql -U litellm_user -d litellm_db -c "SELECT server_name, url, transport, status FROM \"LiteLLM_MCPServerTable\";"

# Network connectivity test
docker exec litellm ping -c 1 mcp-postgres

# MCP service status
docker logs mcp-postgres --tail 10
docker logs litellm --tail 50 | grep -i "mcp\|tool\|function"

# Function calling test
curl -H "Authorization: Bearer sk-litellm-cecca390f610603ff5180ba0ba2674afc8f7689716daf25343de027d10c32404" \
     -H "Content-Type: application/json" \
     -d '{"model": "claude-3-haiku-orchestrator", "messages": [{"role": "user", "content": "Use postgres_list_databases to show databases"}], "tools": [{"type": "function", "function": {"name": "postgres_list_databases", "description": "List PostgreSQL databases", "parameters": {"type": "object", "properties": {}}}}], "tool_choice": "auto"}' \
     http://localhost:4000/chat/completions
```

## Next Steps for Other AI

**PRIMARY FOCUS**: The infrastructure is working correctly. The issue is specifically with LiteLLM's MCP function execution routing after tool_calls generation.

**Recommended Investigation Order**:
1. **Research LiteLLM MCP execution source code** - How does LiteLLM handle the execution phase after generating tool_calls?
2. **Database schema deep dive** - What database associations are required for MCP execution to work?
3. **Alternative LiteLLM versions** - Test with different versions to isolate if this is a version-specific bug
4. **Community solutions** - Search for working LiteLLM MCP configurations and compare with current setup
5. **Direct MCP testing** - Test MCP postgres service independently to verify it can execute functions
6. **Alternative approaches** - Consider bypassing LiteLLM proxy and using direct MCP client if LiteLLM proves unreliable

## Summary for Continuation

**INFRASTRUCTURE STATUS**: ✅ Working (database, authentication, environment variables, model configuration)
**BLOCKING ISSUE**: ❌ LiteLLM MCP function execution phase broken
**ROOT CAUSE**: Unknown - appears to be LiteLLM-specific MCP integration issue
**NEXT ACTION**: Deep investigation of LiteLLM MCP execution architecture and potential workarounds