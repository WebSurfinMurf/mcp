# Unified MCP Tool Registry

## Overview
This directory contains the unified MCP tool system that provides a single source of truth for MCP tool definitions, usable by both Claude Code and LiteLLM.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Central Tool Registry                      │
│                   tool_definitions.py                        │
│                                                              │
│     Defines all MCP tools in one place with schemas         │
└─────────────────┬───────────────────────┬──────────────────┘
                  │                       │
         ┌────────▼────────┐     ┌───────▼────────┐
         │ Claude Adapter  │     │ LiteLLM Adapter│
         │ claude_adapter.py     │ (Coming Soon)   │
         └────────┬────────┘     └───────┬────────┘
                  │                       │
         ┌────────▼────────┐     ┌───────▼────────┐
         │  Claude Code    │     │    LiteLLM     │
         └─────────────────┘     └────────────────┘
                  │                       │
                  └───────────┬───────────┘
                              │
                  ┌───────────▼───────────┐
                  │   MCP Services         │
                  │  (Docker Containers)   │
                  └───────────────────────┘
```

## Components

### 1. tool_definitions.py
Central registry of all MCP tool definitions. Currently includes:
- **filesystem**: File operations (read_file, list_directory)
- **postgres**: Database operations (list_databases, execute_sql)

### 2. tool_bridge.py
Bridge for executing MCP tools via Docker containers. Supports:
- Direct Docker execution
- SSE proxy execution (future)

### 3. claude_adapter.py
MCP server adapter for Claude Code that:
- Implements JSON-RPC over stdio protocol
- Translates unified tool definitions to MCP format
- Executes tools via Docker containers

### 4. litellm_adapter.py (Coming Soon)
Will provide OpenAI-compatible function calling format for LiteLLM.

## Installation

### For Claude Code

1. Add to Claude Code configuration (`~/.config/claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "unified-tools": {
      "command": "/home/administrator/projects/mcp/unified-registry/run_claude_adapter.sh",
      "args": []
    }
  }
}
```

2. Restart Claude Code

3. Available tools will appear with format: `{service}_{tool_name}`
   - `filesystem_read_file`
   - `filesystem_list_directory`
   - `postgres_list_databases`
   - `postgres_execute_sql`

### For LiteLLM (Coming Soon)

The LiteLLM adapter will integrate with the existing middleware at port 4001.

## Testing

### Test Claude Adapter
```bash
# Test initialization and tool listing
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1}
{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}' | python3 claude_adapter.py

# Test tool execution
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1}
{"jsonrpc":"2.0","method":"tools/call","params":{"name":"filesystem_list_directory","arguments":{"path":"/workspace"}},"id":2}' | python3 claude_adapter.py
```

### Test Direct MCP Services
```bash
# Test filesystem service
python3 test_direct.py

# Test bridge functionality
python3 test_bridge.py
```

## Adding New Services

To add a new MCP service:

1. Add service definition to `tool_definitions.py`:
```python
"service_name": {
    "service": "service_name",
    "endpoint": "http://localhost:8585/servers/service/sse",  # For SSE proxy
    "docker_command": ["docker", "run", ...],  # For direct execution
    "tools": [
        {
            "name": "tool_name",
            "mcp_name": "actual_mcp_tool_name",
            "description": "Tool description",
            "parameters_schema": {...}
        }
    ]
}
```

2. Update `claude_adapter.py` `build_docker_command()` method if needed

3. Test the new service

## Current Status

✅ **Completed**:
- Central tool registry design
- Tool definitions for filesystem and postgres
- Claude Code adapter with stdio JSON-RPC
- Direct Docker execution support
- Basic testing infrastructure

🚧 **In Progress**:
- Expanding to all 7 MCP services
- LiteLLM adapter implementation

📋 **Planned**:
- SSE proxy integration
- Comprehensive test suite
- Performance optimization
- Auto-discovery of new services

## Known Issues

1. **Docker Execution**: Some MCP services require specific Docker networking or environment setup
2. **Response Parsing**: MCP servers may not always respond to single requests
3. **Timeout Handling**: Long-running operations need better timeout management

## Dependencies

- Python 3.8+
- aiohttp (for SSE proxy support)
- Docker (for running MCP services)
- Access to MCP service containers

## Security Notes

- Database credentials are hardcoded in adapter for now (should use secrets)
- File system access is controlled by Docker volume mounts
- All MCP services run in isolated containers

## Support

For issues or questions, check:
- `/home/administrator/projects/mcp/` - MCP service configurations
- `/home/administrator/projects/litellm/` - LiteLLM integration
- `/home/administrator/projects/AINotes/` - System documentation