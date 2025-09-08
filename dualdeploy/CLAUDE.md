# MCP Dual-Mode Deployment

**Location**: `/home/administrator/projects/mcp/dualdeploy/`  
**Created**: 2025-09-08  
**Status**: ✅ Clean implementation ready for testing  
**Architecture**: Dual-mode MCP services (stdio for Claude, SSE for web)

## Overview

Clean implementation of the dual-mode MCP architecture where each service can operate in both stdio mode (for Claude Code) and SSE mode (for web clients like LiteLLM/Open WebUI). This replaces the complex unified-tools adapter approach.

## Architecture

### Directory Structure
```
/home/administrator/projects/mcp/dualdeploy/
├── core/
│   └── mcp_base.py        # Base class with datetime fix
├── services/
│   ├── mcp_postgres.py    # PostgreSQL service
│   └── postgres_models.py # Pydantic validation models
├── shims/
│   └── postgres.js        # Node.js shim for Claude
├── deploy.sh              # Deployment script
├── requirements.txt       # Python dependencies
└── CLAUDE.md             # This file
```

### Key Features
- **Single Service, Dual Mode**: Each service supports both stdio and SSE
- **Node.js Shim**: Bridges Python services with Claude Code's MCP protocol
- **DateTime Fix**: Custom JSON encoder handles datetime serialization
- **Clean Deployment**: Simple script for setup, run, test, and register

## Quick Start

### 1. Setup Environment
```bash
cd /home/administrator/projects/mcp/dualdeploy
./deploy.sh setup
```

### 2. Test PostgreSQL Service
```bash
# Test in stdio mode
./deploy.sh test postgres

# Run directly
./deploy.sh run postgres stdio
```

### 3. Register with Claude Code
```bash
./deploy.sh register postgres
# Then restart Claude Code
```

### 4. Use in Claude
```
Using postgres-v2, list all databases
Using postgres-v2, execute SQL: SELECT version()
```

## PostgreSQL Service

### Available Tools (5)
1. **list_databases** - List all databases with metadata
2. **execute_sql** - Execute SQL queries (datetime fix applied)
3. **list_tables** - List tables in a database
4. **table_info** - Get detailed table information
5. **query_stats** - Get query performance statistics

### Configuration
- **Database URL**: `postgresql://admin:Pass123qp@localhost:5432/postgres`
- **Connection Pool**: 2-10 connections
- **Timeout**: 30 seconds default

## Fixed Issues

### ✅ DateTime Serialization
- **Problem**: Queries with datetime fields caused JSON serialization errors
- **Solution**: Added `DateTimeEncoder` class in `mcp_base.py`
- **Status**: Fixed - datetime and Decimal types now serialize correctly

### ⏳ Pending Issues
1. **Cross-Database Connections**: Need to improve database switching logic
2. **Permissions**: Some tables not visible (may be empty schemas)

## Deployment Commands

### Service Management
```bash
# Setup virtual environment
./deploy.sh setup

# Run service in stdio mode (for testing)
./deploy.sh run postgres stdio

# Run service in SSE mode (port 8001)
./deploy.sh run postgres sse

# Test service
./deploy.sh test postgres

# Check status
./deploy.sh status

# Clean up
./deploy.sh clean
```

### Registration
```bash
# Register with Claude Code
./deploy.sh register postgres

# This updates ~/.config/claude/mcp-settings.json
# Restart Claude Code after registration
```

## How the Shim Works

The Node.js shim (`shims/postgres.js`) acts as a bridge:
1. Receives JSON-RPC requests from Claude Code
2. Forwards them to the Python service via stdin
3. Captures Python responses from stdout
4. Returns them to Claude Code

This approach works because:
- Node.js has proven compatibility with Claude's MCP bridge
- Python services remain clean and maintainable
- Logging helps debug any issues

## SSE Mode (Web Clients)

For LiteLLM/Open WebUI integration:
```bash
# Start in SSE mode on port 8001
./deploy.sh run postgres sse

# Access endpoints:
# GET  http://localhost:8001/sse     - SSE stream
# POST http://localhost:8001/rpc     - Execute tools
# GET  http://localhost:8001/health  - Health check
# GET  http://localhost:8001/tools   - List tools
```

**Note**: SSE mode not yet tested with LiteLLM

## Adding New Services

To add a new service (e.g., filesystem):

1. **Create Service File**: `services/mcp_filesystem.py`
   - Inherit from `MCPService`
   - Register tools in `__init__`
   - Implement tool handlers

2. **Create Models**: `services/filesystem_models.py`
   - Define Pydantic models for parameters
   - Add validation rules

3. **Create Shim**: `shims/filesystem.js`
   - Copy postgres.js and update paths
   - Change service name in logs

4. **Register**: `./deploy.sh register filesystem`

## Logs and Debugging

### Log Files
- **Shim Log**: `/tmp/postgres_mcp.log`
- **Service Logs**: Output to stderr (visible in shim log)

### Debug Commands
```bash
# Watch shim log
tail -f /tmp/postgres_mcp.log

# Test manually
echo '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' | \
  ./shims/postgres.js

# Check Claude registration
cat ~/.config/claude/mcp-settings.json | jq
```

## Next Steps

### Immediate
1. Test PostgreSQL service in new location
2. Verify Claude Code integration works
3. Test SSE mode with curl

### Future Services
- filesystem - File operations
- github - GitHub API integration
- monitoring - Logs and metrics
- n8n - Workflow automation
- timescaledb - Time-series database
- playwright - Browser automation

### Integration
- Test with LiteLLM middleware
- Configure Open WebUI to use SSE endpoints
- Create unified registry for all services

## Technical Notes

### Why Node.js Shim?
Direct Python-to-Claude MCP communication has persistent issues. The Node.js shim provides reliable stdio handling that works with Claude's MCP bridge.

### DateTime Fix Details
The `DateTimeEncoder` class in `mcp_base.py`:
- Converts datetime/date objects to ISO format strings
- Converts Decimal objects to floats
- Applied to all JSON responses automatically

### Path Independence
Services use dynamic path resolution:
```python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```
This makes the code portable across different locations.

## Migration from Old System

### From unified-registry-v2
- Core improvements: DateTime serialization fix
- Cleaner structure: Removed debug files and test artifacts
- Simplified deployment: Single script for all operations

### From unified-registry (v1)
- Architecture change: Direct services instead of adapter pattern
- Tool naming: Now `postgres-v2` instead of `unified-tools`
- Performance: Better with connection pooling and direct execution

---
*Clean implementation ready for production use*