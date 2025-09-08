# Project: Unified MCP Tool Registry

## Overview
- **Purpose**: Single source of truth for MCP tool definitions, usable by both Claude Code and LiteLLM
- **Created**: 2025-09-07
- **Updated**: 2025-09-08
- **Status**: Phase 2 Complete - Claude adapter working, 7 services integrated (24 tools)
- **Architecture**: Central registry → Platform adapters → Docker/Node.js MCP services

## Configuration
- **Directory**: `/home/administrator/projects/mcp/unified-registry/`
- **Claude Command**: `/home/administrator/projects/mcp/unified-registry/run_claude_adapter.sh`
- **Tool Format**: `{service}_{tool}` (e.g., `filesystem_list_directory`)

## Services & Tools

### Currently Integrated (7 services, 24 tools) ✅

1. **filesystem** (4 tools) - File operations via Docker
   - `filesystem_read_file` - Read file contents
   - `filesystem_list_directory` - List directory contents
   - `filesystem_write_file` - Write content to files
   - `filesystem_create_directory` - Create directories
   - Docker: `mcp/filesystem`
   - Mount: `/home/administrator` as `/workspace`

2. **postgres** (2 tools) - PostgreSQL operations via Docker
   - `postgres_list_databases` - List all databases
   - `postgres_execute_sql` - Execute SQL queries
   - Docker: `crystaldba/postgres-mcp`
   - Network: `postgres-net`
   - Connection: `postgresql://admin:Pass123qp@postgres:5432/postgres`

3. **github** (3 tools) - GitHub API via npx
   - `github_search_repositories` - Search for repositories
   - `github_get_repository` - Get repository details
   - `github_create_issue` - Create new issues
   - Command: `npx @modelcontextprotocol/server-github`
   - Token: Loaded from `/home/administrator/secrets/github.env`

4. **monitoring** (5 tools) - Loki/Netdata via Node.js
   - `monitoring_search_logs` - Search logs with LogQL
   - `monitoring_get_recent_errors` - Get recent error logs
   - `monitoring_get_container_logs` - Get specific container logs
   - `monitoring_get_system_metrics` - Get system metrics
   - `monitoring_check_service_health` - Check service health
   - Command: `node /home/administrator/projects/mcp/monitoring/src/index.js`

5. **n8n** (3 tools) - Workflow automation via wrapper
   - `n8n_list_workflows` - List all workflows
   - `n8n_get_workflow` - Get workflow details
   - `n8n_execute_workflow` - Execute workflows
   - Command: `bash /home/administrator/projects/mcp/n8n/mcp-wrapper.sh`

6. **playwright** (4 tools) - Browser automation via Node.js
   - `playwright_navigate` - Navigate to URLs
   - `playwright_screenshot` - Take screenshots
   - `playwright_click` - Click elements
   - `playwright_fill` - Fill form fields
   - Command: `node /home/administrator/projects/mcp/playwright/dist/index.js`

7. **timescaledb** (3 tools) - Time-series DB via Docker
   - `timescaledb_list_hypertables` - List hypertables
   - `timescaledb_query_timeseries` - Query time-series data
   - `timescaledb_create_hypertable` - Create hypertables
   - Docker: Via wrapper script
   - Command: `bash /home/administrator/projects/mcp/timescaledb/mcp-wrapper.sh`

### Services NOT Integrated
- **fetch** - Skipped (redundant with WebFetch in Claude Code)
- **memory** - Skipped (broken - onnxruntime-node issues)
- **docker-hub** - Skipped (authentication issues)

## Implementation Files

### Core Components
- `tool_definitions.py` - Central tool registry
- `tool_bridge.py` - Docker/SSE communication layer
- `claude_adapter.py` - Claude Code stdio adapter
- `run_claude_adapter.sh` - Wrapper script for Claude

### Testing
- `test_direct.py` - Direct MCP service testing
- `test_bridge.py` - Bridge functionality testing
- `requirements.txt` - Python dependencies (aiohttp)

### Documentation
- `README.md` - Complete documentation
- `/home/administrator/projects/litellm/mcpbothplan.md` - Implementation plan

## Claude Code Integration

Add to `~/.config/claude/claude_desktop_config.json`:
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

## Testing Commands

### Test Claude Adapter
```bash
# Initialize and list tools
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1}
{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}' | python3 claude_adapter.py

# Execute a tool
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1}
{"jsonrpc":"2.0","method":"tools/call","params":{"name":"filesystem_list_directory","arguments":{"path":"/workspace/projects"}},"id":2}' | python3 claude_adapter.py
```

### Test Direct MCP Services
```bash
cd /home/administrator/projects/mcp/unified-registry
python3 test_direct.py
```

## Technical Details

### Architecture Flow
1. Claude Code calls unified-tools MCP server via stdio
2. Claude adapter receives JSON-RPC request
3. Adapter looks up tool in central registry
4. Executes Docker container with appropriate configuration
5. Parses response and returns to Claude Code

### Docker Execution
- Each MCP service runs in isolated container
- Networking configured per service (postgres-net, etc.)
- Volume mounts for filesystem access
- Environment variables for credentials

### Tool Naming Convention
- Format: `{service}_{tool}`
- Service prefix helps identify which MCP service handles the tool
- Prevents naming conflicts between services

## Troubleshooting

### Common Issues
1. **"No valid response from tool"**
   - MCP services may not respond to single requests
   - Check Docker container logs

2. **Connection refused**
   - Ensure Docker network is configured
   - Check if MCP container image exists

3. **Permission denied**
   - Verify volume mount permissions
   - Check Docker user configuration

## Implementation Notes

### 2025-09-07: Initial Implementation
- Created central registry with 2 example services
- Built Claude adapter with stdio JSON-RPC protocol
- Validated Docker execution for filesystem and postgres
- Established tool naming convention
- Created testing infrastructure

### 2025-09-08: Phase 2 Expansion
- Added 5 more MCP services (github, monitoring, n8n, playwright, timescaledb)
- Extended to 24 total tools across 7 services
- Updated adapter to handle both Docker and Node.js services
- Added environment variable support for services
- Fixed Python boolean values in tool definitions
- Documented skipped services (fetch, memory, docker-hub)

### 2025-09-08 Evening: Node.js Shim Solution for v2
- Identified Python-MCP bridge communication issue in unified-registry-v2
- Implemented Node.js shim wrapper to handle stdio communication
- Added minimal echo test for diagnostics
- Updated postgres-v2 to use enhanced shim wrapper
- Solution ready for testing in `/home/administrator/projects/mcp/unified-registry-v2/`

### Key Decisions
- Use Docker containers for MCP service execution (not direct processes)
- Single registry file for all tool definitions
- Platform-specific adapters translate from central registry
- Hardcode PostgreSQL connection due to Docker env expansion issues

## Next Steps
1. ✅ Create central tool registry
2. ✅ Build Claude Code adapter
3. ✅ Add 7 MCP services (24 tools total)
4. ⏳ Build LiteLLM HTTP/SSE adapter
5. ⏳ Connect to MCP middleware at port 4001
6. ⏳ Replace mock tools with real execution
7. ⏳ Test end-to-end with Open WebUI

## Security Notes
- PostgreSQL credentials currently hardcoded (should use secrets)
- Filesystem access controlled by Docker volume mounts
- Each MCP service runs in isolated container
- No network access between MCP containers

## References
- MCP Protocol: https://modelcontextprotocol.io/
- Original MCP services: `/home/administrator/projects/mcp/`
- LiteLLM integration: `/home/administrator/projects/litellm/`
- SSE Proxy: `/home/administrator/projects/mcp/proxy-sse/`

---
*Last Updated: 2025-09-07*
*Status: Phase 1 Complete - Ready for expansion*