# MCP Integration Concerns and Current Status

## 📋 Current Implementation Status

### What's Working ✅
1. **LiteLLM Proxy**: Running at `localhost:4000` with v1.77.3-stable
2. **MCP PostgreSQL Container**: Running crystaldba/postgres-mcp with SSE transport on port 8080
3. **Network Connectivity**: Both containers connected via `litellm-mcp-net` bridge network
4. **SSE Endpoint**: MCP postgres responding to SSE connections with proper event stream
5. **Tool Discovery**: HTTP endpoint `/v1/mcp/tools` returns full list of PostgreSQL tools:
   - `db_main-list_schemas`
   - `db_main-execute_sql`
   - `db_main-explain_query`
   - `db_main-analyze_db_health`
   - And 6 other database tools

### Configuration Details 📝
- **LiteLLM Config**: SSE transport pointing to `http://mcp-postgres:8080/sse`
- **Claude Code Config**: SSE transport pointing to `http://localhost:4000/mcp/`
- **Authentication**: Master key `sk-litellm-cecca390f610603ff5180ba0ba2674afc8f7689716daf25343de027d10c32404`
- **MCP Server ID**: `db_main` (referenced in both configs)

## ⚠️ Primary Concerns

### 1. **Claude Code CLI MCP Integration Protocol**
**Problem**: When I test MCP tool calls, I get "No such tool available" errors
**Unknown**:
- Does Claude Code CLI properly support SSE-based MCP gateways?
- What is the exact protocol Claude Code expects from MCP servers?
- Does Claude Code work with LiteLLM's MCP gateway specifically?

### 2. **LiteLLM MCP Gateway Endpoint Behavior**
**Observed**:
- `/mcp/` endpoint returns: "Not Acceptable: Client must accept text/event-stream"
- `/v1/mcp/tools` endpoint works for listing tools via HTTP
- Cannot find working endpoint for actual tool execution

**Unknown**:
- What is the correct endpoint format for LiteLLM MCP tool execution?
- Is there a separate endpoint for SSE connections vs tool calls?
- Are there specific headers or request formats required?

### 3. **Transport Protocol Mismatch**
**Issue**: Mixed signals about HTTP vs SSE
- LiteLLM shows tools via HTTP (`/v1/mcp/tools`)
- LiteLLM MCP communication expects SSE (`/mcp/` with event-stream headers)
- Claude Code configuration supports both transports but unclear which works

**Unknown**:
- Should Claude Code use `transport: "http"` or `transport: "sse"`?
- Is there a hybrid approach where discovery is HTTP but execution is SSE?

### 4. **Session Management and Headers**
**Current Headers**:
```json
{
  "Authorization": "Bearer sk-litellm-...",
  "x-mcp-servers": "db_main"
}
```

**Unknown**:
- Is `x-mcp-servers` the correct header for server selection?
- Does Claude Code need additional session management?
- Are there required headers for SSE upgrade?

## 🔍 Specific Questions for Research

### For Claude Code CLI Documentation:
1. What is the exact MCP protocol Claude Code CLI implements?
2. Does Claude Code support MCP gateways/proxies or only direct server connections?
3. What are the required headers and request formats for Claude Code MCP?
4. Are there examples of Claude Code connecting to LiteLLM MCP gateways?

### For LiteLLM MCP Documentation:
1. What is the correct endpoint format for MCP tool execution (not just discovery)?
2. How should clients authenticate and execute tools through LiteLLM MCP gateway?
3. Are there working examples of external MCP clients connecting to LiteLLM?
4. What are the exact SSE connection requirements and message formats?

### For MCP Protocol Specification:
1. What is the standard way to proxy MCP connections through gateways?
2. How should transport negotiation work between clients and gateways?
3. Are there standard headers for server selection in multi-server setups?

## 🧪 Test Cases to Validate

### Test 1: Direct MCP Connection (Bypass Gateway)
```json
{
  "mcpServers": {
    "postgres-direct": {
      "transport": "sse",
      "url": "http://localhost:48010/sse"
    }
  }
}
```
**Purpose**: Determine if issue is with gateway or with Claude Code MCP integration

### Test 2: LiteLLM Gateway Tool Execution
Need to find correct endpoint format for:
- Making actual tool calls (not just listing)
- Passing parameters to tools
- Receiving tool responses

### Test 3: Claude Code MCP Session Debugging
- Enable verbose logging in Claude Code CLI
- Capture actual HTTP/SSE traffic during MCP connection attempts
- Compare against working MCP implementations

## 📁 File Locations for Reference
- **LiteLLM Config**: `/home/administrator/projects/litellm/config/config.yaml`
- **Claude Code Config**: `/home/administrator/.config/claude/mcp-settings.json`
- **LiteLLM Logs**: `docker logs litellm`
- **MCP Logs**: `docker logs mcp-postgres`

## 🔍 RESEARCH FINDINGS - KEY ANSWERS

### ✅ Claude Code CLI MCP Support
**CONFIRMED**: Claude Code CLI supports both SSE and HTTP transports for MCP servers
- **Commands**: `claude mcp add --transport sse <name> <url>` or `claude mcp add --transport http <name> <url>`
- **Streamable HTTP**: New protocol combining HTTP with SSE for bidirectional communication
- **Authentication**: Supports OAuth 2.0 and Bearer token in Authorization header

### ✅ LiteLLM MCP Gateway Architecture
**CONFIRMED**: LiteLLM has native MCP Gateway functionality
- **Endpoint**: `/v1/responses` for tool execution (NOT `/mcp/` or `/v1/mcp/tools`)
- **Tool Discovery**: LiteLLM fetches MCP tools and converts to OpenAI-compatible definitions
- **Auto Execution**: With `require_approval: "never"` triggers automatic tool execution
- **Server Selection**: Uses `x-mcp-servers` header for server selection

### 🔧 CORRECT CONFIGURATION NEEDED

**Claude Code CLI should use**:
```bash
claude mcp add --transport sse litellm-gateway http://localhost:4000/mcp
```

**Tool Execution Endpoint**:
```
POST http://localhost:4000/v1/responses
Headers:
- Authorization: Bearer <master_key>
- x-mcp-servers: db_main
- Content-Type: application/json

Body:
{
  "model": "gpt-4o-mock",
  "tools": [{"type": "mcp", "server_label": "litellm", "server_url": "http://localhost:4000/mcp"}],
  "input": "list database schemas",
  "tool_choice": "required"
}
```

## 🎯 Expected Outcome
After applying correct configuration:
1. Claude Code CLI connects to LiteLLM MCP gateway via SSE transport
2. Tool execution goes through `/v1/responses` endpoint
3. PostgreSQL MCP tools become available in Claude Code CLI
4. Database operations work seamlessly through the gateway

## 🚨 ACTION REQUIRED
**MEDIUM** - Need to reconfigure with correct endpoints and test the proper LiteLLM MCP gateway integration pattern.

---
*Created: 2025-09-21*
*Updated with research findings: 2025-09-21*
*Purpose: Document current status and research needs for external AI consultation*