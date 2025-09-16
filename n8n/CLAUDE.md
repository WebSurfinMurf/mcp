# Project: mcp-n8n

**Status**: ✅ **SUPERSEDED BY DIRECT API INTEGRATION** - See main MCP server implementation
**Current Implementation**: Direct API calls in `/home/administrator/projects/mcp/server/app/main.py`
**Integration Status**: **FULLY OPERATIONAL** as of 2025-09-16

## Quick Reference - Current Implementation
```bash
# Test n8n tools via main MCP server
curl -X POST http://localhost:8001/tools/n8n_list_workflows -H "Content-Type: application/json" -d '{"input": {}}'
curl -X POST http://localhost:8001/tools/n8n_get_database_statistics -H "Content-Type: application/json" -d '{"input": {}}'

# Check n8n service status
docker ps | grep n8n

# View current API key configuration
grep N8N_API_KEY /home/administrator/secrets/mcp-server.env
```

## Overview - Implementation Evolution
- **Original Purpose**: Standalone MCP server for n8n workflow automation integration
- **Created**: 2025-09-05
- **Status Change**: **SUPERSEDED** by direct API integration in main MCP server (2025-09-16)
- **Current Status**: **FULLY OPERATIONAL** via direct API integration
- **n8n Instance**: http://n8n:5678 (internal Docker network)

## Architecture Evolution

### **Original Architecture (2025-09-05 to 2025-09-16)**
Standalone MCP server pattern:
```
Claude Code → mcp-wrapper.sh → Node.js MCP Server → n8n API
```

### **Current Architecture (2025-09-16+)**
Direct API integration in main MCP server:
```
Claude Code → MCP Server (mcp-server:8000) → Direct HTTP calls → n8n API (n8n:5678)
```

## Current Configuration
- **Implementation Location**: `/home/administrator/projects/mcp/server/app/main.py`
- **Environment File**: `/home/administrator/secrets/mcp-server.env`
- **Connection**: Direct HTTP to n8n at `http://n8n:5678/api/v1`
- **Authentication**: `X-N8N-API-KEY` header with JWT token

## Available Tools (Current Implementation)

### **n8n Workflow Tools (3 tools) - ✅ FULLY OPERATIONAL**
1. **`n8n_list_workflows`** - List all n8n workflows with metadata
   - Returns: workflow summary with ID, name, active status, node count

2. **`n8n_get_workflow`** - Get detailed workflow information by ID
   - Parameters: `workflow_id` (string)
   - Returns: comprehensive workflow details including node types, tags, timestamps

3. **`n8n_get_database_statistics`** - Get n8n instance statistics
   - Returns: total workflows, active/inactive counts, node statistics, available node types

## MCP Resources
- `n8n://workflows` - List of all workflows
- `n8n://executions/recent` - Recent execution history
- `n8n://status` - Current n8n instance status

## Deployment
No deployment needed - MCP servers run via stdio when called by Claude Code.
Setup steps:
1. Install dependencies: `cd /home/administrator/projects/mcp-n8n && npm install`
2. Ensure n8n is running with exposed port: `docker ps | grep n8n`
3. API key is configured in `/home/administrator/secrets/n8n-mcp.env`
4. Wrapper script at `mcp-wrapper.sh` loads credentials

## Current Integration (2025-09-16+)
Integrated directly into main MCP server:
- **Main Server**: `http://mcp-server:8000` (internal) / `http://localhost:8001` (bridge)
- **Tool Access**: Available via Claude Code MCP tools
- **Security**: API credentials in `/home/administrator/secrets/mcp-server.env`

### Usage in Claude Code (Current)
Access n8n tools through the main MCP infrastructure:
```bash
# Using MCP tools directly
n8n_list_workflows
n8n_get_workflow workflow_id="some-id"
n8n_get_database_statistics

# Or via HTTP API
curl -X POST http://localhost:8001/tools/n8n_list_workflows \
  -H "Content-Type: application/json" -d '{"input": {}}'
```

## Environment Variables

### **Current Configuration** (in `/home/administrator/secrets/mcp-server.env`):
- **N8N_API_URL**: `http://n8n:5678/api/v1` (internal Docker network)
- **N8N_API_KEY**: JWT token for API authentication (obtained from n8n UI)

### **Legacy Configuration** (in `/home/administrator/secrets/n8n-mcp.env`):
- **N8N_URL**: http://linuxserver.lan:5678
- **N8N_API_KEY**: JWT token for API authentication

## Monitoring & Testing
```bash
# Test MCP server directly
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | /home/administrator/projects/mcp-n8n/mcp-wrapper.sh

# Test n8n API connectivity
curl -H "X-API-Key: $(grep N8N_API_KEY /home/administrator/secrets/n8n-mcp.env | cut -d= -f2-)" \
  http://linuxserver.lan:5678/api/v1/workflows

# Check n8n container status
docker ps | grep n8n

# View n8n logs
docker logs n8n --tail 50
```

## Troubleshooting

### MCP Server Not Starting
- Check Node.js version: `node --version` (needs v18+)
- Verify dependencies installed: `cd /home/administrator/projects/mcp-n8n && npm list`
- Test wrapper script: `echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | ./mcp-wrapper.sh`

### Cannot Connect to n8n
- Verify n8n is running: `docker ps | grep n8n`
- Check port is exposed: `docker port n8n` (should show 5678)
- Test API directly: `curl http://linuxserver.lan:5678/api/v1/workflows`
- Verify API key in `/home/administrator/secrets/n8n-mcp.env`

### MCP Not Available in Claude Code
- Restart Claude Code after configuration changes
- Verify configuration in `/home/administrator/projects/.mcp.json`
- Check wrapper script is executable: `ls -l mcp-wrapper.sh`
- View Claude Code logs for MCP errors

## API Key Management
To update or regenerate the API key:
1. Generate new API key in n8n UI (Settings → API)
2. Update `/home/administrator/secrets/n8n-mcp.env` with new key
3. Test: `echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | ./mcp-wrapper.sh`
4. Restart Claude Code

## Implementation Notes

### 2025-09-16: Migration to Direct API Integration ✅ **CURRENT**
- **Architecture Change**: Replaced standalone MCP server with direct API integration
- **Problem Solved**: Eliminated mcp-n8n container restart loops and orchestrator complexity
- **Implementation**: Added 3 n8n tools directly to main MCP server (`/mcp/server/app/main.py`)
- **Environment Fix**: Corrected `N8N_API_URL` loading by sourcing environment before docker-compose
- **Security**: Maintained secure credential management in `/secrets/mcp-server.env`
- **Tools Operational**: All 3 n8n tools fully functional via direct API calls
- **Benefits**: Simplified architecture, reliable connectivity, integrated with 31-tool infrastructure

### 2025-09-05: Initial Deployment (Legacy)
- Created standalone MCP n8n server implementation
- Runs directly via Node.js (not containerized)
- Integrated with Claude Code configuration
- Provides access to 8 workflow management tools
- Fixed missing npm dependencies issue
- Updated to use linuxserver.lan:5678 for API access
- Moved API credentials to secure environment file
- Created wrapper script for secure credential loading
- Successfully tested authentication with n8n API

### Features
- Full workflow management capabilities
- Execution monitoring and control
- Webhook testing support
- Resource endpoints for batch operations

### Security Notes
- API credentials stored securely in /home/administrator/secrets/n8n-mcp.env
- Wrapper script loads credentials at runtime (no hardcoded secrets)
- File permissions set to 600 on environment file
- JWT token expires in 2026 (check n8n for renewal)
- Runs with limited permissions

## Migration Information

### **For Current Usage (2025-09-16+)**
- **Use**: Main MCP server tools (`n8n_list_workflows`, `n8n_get_workflow`, `n8n_get_database_statistics`)
- **Access**: Via Claude Code MCP tools or HTTP API at `localhost:8001`
- **Documentation**: See `/home/administrator/projects/mcp/server/CLAUDE.md`

### **Legacy Standalone Server**
- **Status**: Superseded but preserved for reference
- **Directory**: `/home/administrator/projects/mcp/n8n/` (this location)
- **Use Case**: Reference implementation for standalone MCP servers

## References
- n8n Documentation: https://docs.n8n.io/api/
- MCP SDK: https://github.com/anthropics/model-context-protocol
- Main n8n Instance: Internal Docker network `http://n8n:5678`
- Main MCP Server: `/home/administrator/projects/mcp/server/`

---
*Last Updated: 2025-09-16*
*Status: Superseded by direct API integration in main MCP server*