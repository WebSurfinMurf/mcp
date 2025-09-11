# Project: mcp-n8n

## Quick Reference
```bash
# Test MCP server
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | ./mcp-wrapper.sh

# Check n8n status
docker ps | grep n8n

# View API key
grep N8N_API_KEY /home/administrator/secrets/n8n-mcp.env
```

## Overview
- **Purpose**: MCP server for n8n workflow automation integration with Claude Code
- **Created**: 2025-09-05
- **Version**: 1.0.0
- **Status**: Active and configured
- **n8n Instance**: https://n8n.ai-servicers.com

## Architecture
MCP (Model Context Protocol) server that provides Claude Code with direct access to n8n workflow automation capabilities:
- List and manage workflows
- Execute workflows programmatically
- Monitor execution status
- Access workflow history

## Configuration
- **Source Directory**: /home/administrator/projects/mcp-n8n
- **Environment File**: /home/administrator/secrets/n8n-mcp.env
- **Wrapper Script**: mcp-wrapper.sh (loads environment variables)
- **Connection**: HTTP to n8n at linuxserver.lan:5678

## MCP Tools Available

### Workflow Management
- `list_workflows` - List all workflows with optional filtering
- `get_workflow` - Get details of a specific workflow
- `activate_workflow` - Activate a workflow
- `deactivate_workflow` - Deactivate a workflow

### Workflow Execution
- `execute_workflow` - Execute a workflow by ID or name
- `get_executions` - Get recent workflow execution history
- `get_execution_details` - Get details of a specific execution
- `create_webhook_test` - Generate webhook test payloads

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

## Claude Code Integration
Added to MCP servers configuration at:
- **File**: /home/administrator/projects/.mcp.json
- **Server Name**: n8n
- **Command**: /home/administrator/projects/mcp-n8n/mcp-wrapper.sh
- **Security**: API credentials loaded from secrets/n8n-mcp.env

### Usage in Claude Code
After restarting Claude Code, use n8n commands:
```
# List all workflows
list_workflows

# Get specific workflow
get_workflow id="workflow-id"

# Execute a workflow
execute_workflow id="workflow-id" data='{"key": "value"}'

# Check recent executions
get_executions limit=10 status="success"
```

## Environment Variables
Stored securely in `/home/administrator/secrets/n8n-mcp.env`:
- **N8N_URL**: http://linuxserver.lan:5678
- **N8N_API_KEY**: JWT token for API authentication (obtained from n8n UI)

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

### 2025-09-05: Initial Deployment
- Created MCP n8n server implementation
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

## References
- n8n Documentation: https://docs.n8n.io/api/
- MCP SDK: https://github.com/anthropics/model-context-protocol
- Main n8n Instance: https://n8n.ai-servicers.com

---
*Last Updated: 2025-09-05*