# MCP SSE Services - Design Change: /mcp vs /sse Endpoints

**Date**: 2025-09-10  
**Context**: LiteLLM Integration Issues with SSE  
**Decision**: Switch from `/sse` to `/mcp` as primary endpoint  

## Problem Statement

Originally, MCP SSE services were designed with `/sse` as the primary endpoint for Server-Sent Events streams. However, when attempting to integrate with LiteLLM, we encountered JSON parsing errors:

```
"Unexpected token 'd', "data: {"id"... is not valid JSON"
```

## Root Cause Analysis

1. **SSE Format Incompatibility**: Server-Sent Events streams use the format:
   ```
   data: {"jsonrpc":"2.0","result":...}
   
   event: endpoint
   data: {"endpoints":[...]}
   ```

2. **LiteLLM Expectation**: LiteLLM expects clean JSON responses, not SSE-formatted streams with `data:` prefixes.

3. **Protocol Mismatch**: LiteLLM's MCP integration expects HTTP JSON-RPC endpoints, not SSE streams.

## Design Decision: Switch to /mcp Endpoint

### Rationale

1. **MCP 2025-03-26 Specification Compliance**:
   - Official MCP specification uses HTTP transport with JSON-RPC 2.0
   - GET requests return server capabilities and tool schemas
   - POST requests handle JSON-RPC method calls (initialize, tools/list, tools/call)

2. **LiteLLM Compatibility**:
   - LiteLLM configuration expects URL endpoints that return clean JSON
   - Transport type "http" in LiteLLM points to standard HTTP endpoints
   - No SSE stream parsing required

3. **Industry Standard**:
   - Language Server Protocol (LSP) uses similar HTTP+JSON-RPC pattern
   - JSON-RPC 2.0 is widely supported by tools and proxies
   - Cleaner integration with web-based AI platforms

### Implementation

The `/mcp` endpoint now supports:

1. **GET /mcp**: Returns server info, capabilities, and tool schemas
   ```json
   {
     "jsonrpc": "2.0",
     "result": {
       "protocolVersion": "2025-03-26",
       "capabilities": {"tools": {"listChanged": true}},
       "serverInfo": {"name": "postgres", "version": "1.0.0"},
       "tools": [...]
     }
   }
   ```

2. **POST /mcp**: Handles JSON-RPC method calls
   - `initialize`: Handshake protocol
   - `tools/list`: List available tools
   - `tools/call`: Execute tools with arguments

3. **HEAD /mcp**: Health check for connectivity

### Benefits

1. **Direct Integration**: LiteLLM can directly connect without SSE parsing
2. **Standard Protocol**: Uses established JSON-RPC patterns
3. **Tool Discovery**: GET requests expose all tools and schemas
4. **Backward Compatibility**: SSE endpoints still available at `/sse`
5. **Debugging**: Clean JSON responses easier to debug

### SSE Endpoint Preserved

The `/sse` endpoint remains available for:
- Real-time event streaming
- Debugging and development
- Alternative client implementations that prefer SSE

## Protocol Flow

### LiteLLM Integration
```
LiteLLM --> GET /mcp --> Tool Discovery
LiteLLM --> POST /mcp --> Tool Execution
```

### SSE Alternative (Still Available)
```
Client --> GET /sse --> SSE Stream with events:
  - connection: Server info
  - endpoint: Tool schemas  
  - ping: Keepalive
```

## Configuration Impact

### LiteLLM Configuration
```yaml
mcp_servers:
  postgres_mcp:
    url: "http://localhost:8001/mcp"
    transport: "http"
```

### Alternative SSE Configuration (Deprecated)
```yaml
# Not recommended - causes JSON parsing errors
mcp_servers:
  postgres_mcp:
    url: "http://localhost:8001/sse"
    transport: "sse"
```

## Security Considerations

1. **Input Validation**: Both endpoints use Pydantic schema validation
2. **Error Handling**: Proper JSON-RPC error responses
3. **Network Isolation**: Services still run on Docker networks
4. **Authentication**: Framework ready for token-based auth

## Future Considerations

1. **Deprecation Path**: May eventually deprecate `/sse` in favor of `/mcp`
2. **WebSocket Support**: Could add `/ws` for bidirectional communication
3. **Authentication**: Add OAuth2/JWT support to `/mcp` endpoint
4. **Rate Limiting**: Implement per-client rate limits

## Alternative Approaches Considered

1. **Fix SSE Parsing**: Modify LiteLLM to parse SSE streams correctly
   - Rejected: External dependency, not under our control

2. **Dual Format SSE**: Return plain JSON on specific headers
   - Rejected: Violates SSE specification

3. **Proxy Layer**: Add HTTP-to-SSE translation layer
   - Rejected: Unnecessary complexity

4. **WebSocket Protocol**: Use WebSocket instead of HTTP
   - Rejected: LiteLLM doesn't support WebSocket MCP transport

## Conclusion

The switch from `/sse` to `/mcp` as the primary endpoint provides:
- Immediate LiteLLM compatibility
- Standards compliance with MCP 2025-03-26
- Cleaner integration patterns
- Better debugging experience

This design change prioritizes practical integration while maintaining the underlying MCP protocol integrity and preserving backward compatibility through the preserved `/sse` endpoint.