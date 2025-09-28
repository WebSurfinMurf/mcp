# n8n MCP Service Notes

## Service Overview
**Purpose**: Workflow automation and API integration management
**Type**: Custom FastAPI MCP server with n8n API integration
**Port**: 9074
**Network**: n8n-net (connects to n8n container)

## Core Capabilities
- **Workflow Management**: List, activate, and execute workflows
- **Execution Monitoring**: Track workflow runs and results
- **Credential Access**: Manage API keys and authentication
- **Automation Trigger**: Manual and programmatic workflow execution
- **Integration Hub**: Connect to hundreds of external services

## Available Tools
1. **`get_workflows()`** - List all available workflows
2. **`get_workflow_details(workflow_id)`** - Get detailed workflow information
3. **`activate_workflow(workflow_id)`** - Activate or deactivate workflows
4. **`execute_workflow(workflow_id, data={})`** - Trigger workflow execution
5. **`get_executions(workflow_id, limit=10)`** - Get workflow execution history
6. **`get_credentials()`** - List available credential configurations

## n8n Connection
- **Host**: n8n (via n8n-net)
- **Port**: 5678
- **API Key**: JWT token for authentication
- **API Version**: REST API v1
- **Protocol**: HTTP (internal network)
- **Timeout**: 30 seconds for API calls

## Workflow Capabilities
- **Node Types**: 400+ integrations (APIs, databases, files)
- **Triggers**: Webhooks, schedules, manual execution
- **Data Processing**: JSON manipulation, transformations
- **Conditional Logic**: IF/THEN workflows and routing
- **Error Handling**: Retry policies and error workflows

## Technical Implementation
- **Framework**: FastAPI with aiohttp HTTP client
- **Authentication**: Bearer token (JWT) authentication
- **Network**: Isolated n8n-net Docker network
- **Async Operations**: Non-blocking workflow execution
- **Error Handling**: Comprehensive API error handling

## Client Registration
**Codex CLI**: `codex mcp add n8n python3 /home/administrator/projects/mcp/n8n/mcp-bridge.py`
**Claude Code**: `claude mcp add n8n http://127.0.0.1:9074/sse --transport sse --scope user`

## Common Use Cases
- **Data Synchronization**: Between different systems and APIs
- **Notification Systems**: Email, Slack, webhook notifications
- **File Processing**: Automated file transformations and transfers
- **API Integration**: Connect disparate services and systems
- **Scheduled Tasks**: Automated recurring operations

## Workflow Execution
- **Manual Triggers**: Direct execution via MCP tools
- **Data Input**: JSON payload for workflow parameters
- **Execution Tracking**: Real-time status and results
- **Output Capture**: Workflow results and error messages
- **History**: Complete execution log and audit trail

## API Authentication
- **Token Type**: JWT (JSON Web Token)
- **Scope**: Full API access for workflow management
- **Expiration**: Configurable token lifetime
- **Security**: Network-isolated API communication
- **Credentials**: Stored in environment configuration

## Troubleshooting
- **API Unauthorized**: Verify JWT token is valid
- **Workflow Not Found**: Check workflow ID exists
- **Execution Failed**: Review workflow logic and dependencies
- **Connection Timeout**: Verify n8n container health
- **Permission Denied**: Check workflow access permissions

## Workflow Types
- **Trigger Workflows**: Start automatically on events
- **Manual Workflows**: Require explicit execution
- **Sub-workflows**: Called by other workflows
- **Error Workflows**: Handle failure scenarios
- **Template Workflows**: Reusable workflow patterns

## Integration Examples
- **Database → Spreadsheet**: Sync data automatically
- **Webhook → Email**: Process and notify on events
- **File Upload → Processing**: Automated file handling
- **API Polling → Actions**: Monitor and respond to changes
- **Schedule → Reports**: Generate periodic reports

## Security Model
- **Network Isolation**: Limited to n8n-net communication
- **API Authentication**: JWT token-based security
- **Credential Management**: Secure credential storage in n8n
- **Workflow Permissions**: User-based access control

## Integration Points
- **n8n Container**: Main workflow automation engine
- **n8n-net**: Docker network for API communication
- **Environment File**: `/home/administrator/secrets/mcp-n8n.env`
- **Bridge Script**: `/home/administrator/projects/mcp/n8n/mcp-bridge.py`
- **API Endpoint**: `http://n8n:5678/api/v1/`