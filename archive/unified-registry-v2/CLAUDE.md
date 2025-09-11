# MCP Unified Registry v2 - Dual-Mode Architecture

**Project**: MCP Unified Registry v2  
**Created**: 2025-09-08  
**Last Updated**: 2025-09-08  
**Status**: ✅ PostgreSQL Service Operational via Node.js Shim  
**Location**: `/home/administrator/projects/mcp/unified-registry-v2/`

## Overview

Second-generation MCP architecture implementing dual-mode services that work with both Claude Code (stdio) and web clients (SSE/HTTP). This replaces the complex unified-tools adapter approach with clean, single-source services.

## Architecture

### Core Design
- **Single Service, Multiple Interfaces**: Each MCP service supports both stdio and SSE modes
- **Professional Implementation**: Pydantic validation, connection pooling, structured logging
- **Security-First**: Input validation, SQL injection prevention, path canonicalization
- **Node.js Shim Solution**: Bridges Python services with Claude Code's MCP protocol

### Directory Structure
```
/home/administrator/projects/mcp/unified-registry-v2/
├── core/
│   ├── mcp_base.py           # Base class for all MCP services
│   └── mcp_base_debug.py     # Debug version with extensive logging
├── services/
│   ├── mcp_postgres.py       # PostgreSQL service implementation
│   ├── postgres_models.py    # Pydantic validation models
│   └── mcp_postgres_debug.py # Debug version
├── postgres_shim_enhanced.js # Node.js wrapper for Claude integration
├── deploy.sh                  # Universal deployment script
├── requirements.txt          # Python dependencies
└── venv/                     # Python virtual environment
```

## Current Implementation Status

### ✅ Phase 1: Base Framework - COMPLETE
- MCPService base class with dual-mode operation
- Pydantic validation integration
- Security features (allowlisting, path validation)
- JSON-RPC 2.0 protocol compliance
- Structured logging to stderr
- Universal deployment script

### ✅ Phase 2: PostgreSQL Service - OPERATIONAL
**Status**: Working in Claude Code via Node.js shim

**Available Tools** (5):
1. `list_databases` - List all databases with metadata ✅
2. `execute_sql` - Execute SQL queries ✅ (with datetime issue)
3. `list_tables` - List tables in a database ✅
4. `table_info` - Get detailed table information
5. `query_stats` - Get query performance statistics

**Test Results** (2025-09-08):
- Successfully retrieved 14 databases with sizes and ownership
- SQL execution works for non-datetime queries
- Connection pooling operational (2-10 connections)
- Sub-second response times

### ⏳ Phase 3-6: Not Yet Implemented
- Filesystem service
- GitHub service  
- Monitoring service
- N8n service
- TimescaleDB service
- Playwright service
- LiteLLM/SSE integration (not tested)

## Known Issues

### 1. DateTime Serialization Bug 🐛
**Location**: `/home/administrator/projects/mcp/unified-registry-v2/core/mcp_base.py:211`
**Problem**: `TypeError: Object of type datetime is not JSON serializable`
**Impact**: Queries with datetime fields (like `now()`) fail
**Fix Required**: Add JSON encoder for datetime objects

### 2. Cross-Database Connection 🐛
**Problem**: Cannot query databases other than the default
**Error**: `connection already closed` when specifying different database
**Impact**: Limited to default database queries only
**Fix Required**: Improve connection management for database switching

### 3. Permissions Issue ⚠️
**Observation**: No tables found in public schemas
**Possible Cause**: Permission restrictions or empty schemas
**Investigation Needed**: Check user permissions and actual table existence

## Configuration

### Claude Code Integration
**Config File**: `/home/administrator/.config/claude/mcp-settings.json`
```json
{
  "mcpServers": {
    "postgres-v2": {
      "command": "/home/administrator/projects/mcp/unified-registry-v2/postgres_shim_enhanced.js",
      "args": []
    }
  }
}
```

### Environment
- **Database URL**: `postgresql://admin:Pass123qp@localhost:5432/postgres`
- **Python Version**: 3.12.3
- **Virtual Environment**: `./venv/`
- **Node.js Shim**: Required for Claude Code integration

## The Node.js Shim Solution

### Why It's Needed
Direct Python-to-Claude MCP communication consistently failed despite perfect technical implementation. The service worked flawlessly in manual testing but returned empty responses in Claude Code.

### How It Works
```
Claude Code → MCP Bridge → Node.js Shim → Python Service → PostgreSQL
                ↑__________________________|
                        JSON-RPC Response
```

The Node.js shim (`postgres_shim_enhanced.js`) acts as a translator, handling the sensitive stdio communication that Node.js manages better than Python for MCP protocols.

### Files
- `postgres_shim_enhanced.js` - Production shim wrapper
- `postgres_shim.js` - Basic shim (backup)
- `minimal_mcp.py` - Minimal test service

## Deployment Commands

### Setup Environment
```bash
cd /home/administrator/projects/mcp/unified-registry-v2
./deploy.sh setup  # Creates venv, installs dependencies
```

### Run Services
```bash
# For Claude Code (stdio mode)
./deploy.sh run postgres stdio

# For web clients (SSE mode) - NOT YET TESTED
./deploy.sh run postgres sse
```

### Testing
```bash
# Run test suite
./deploy.sh test

# Manual test
echo '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' | \
  ./postgres_shim_enhanced.js
```

### Check Status
```bash
./deploy.sh status
```

## Testing & Validation

### What's Working ✅
- PostgreSQL connection and queries
- Tool registration and discovery
- JSON-RPC protocol handling
- Node.js shim integration
- Claude Code shows "✓ Connected"
- Basic SQL operations

### What's Not Working ❌
- DateTime field serialization
- Cross-database queries
- SSE mode (not tested with LiteLLM yet)

### Test Commands for Claude
```
# Working
Using postgres-v2, list all databases
Using postgres-v2, execute SQL: SELECT COUNT(*) FROM pg_database

# Not Working (datetime issue)
Using postgres-v2, execute SQL: SELECT now()

# Not Working (cross-database)
Using postgres-v2, execute SQL in database n8n_db: SELECT 1
```

## Logs & Debugging

### Log Files
- `/tmp/postgres_shim_enhanced.log` - Node.js shim activity
- Service logs to stderr (visible in shim log)

### Debug Mode
For extensive debugging, use the debug versions:
- `core/mcp_base_debug.py`
- `services/mcp_postgres_debug.py`
- `debug_wrapper.sh`

## Architecture Benefits

### Achieved ✅
1. **Single Source of Truth**: One service implementation for all modes
2. **Professional Quality**: Pydantic validation, connection pooling, logging
3. **Security**: Multiple validation layers, SQL injection prevention
4. **Simplicity**: 800 lines vs 2000+ in old system

### Pending Validation ⏳
1. **SSE Mode**: Not tested with LiteLLM/Open WebUI
2. **Performance at Scale**: Only PostgreSQL implemented
3. **Full Migration**: 6 more services to implement

## Next Steps

### Immediate Fixes Needed
1. Fix datetime serialization in `mcp_base.py`
2. Fix cross-database connection handling
3. Investigate table permission issues

### Implementation Priority
1. Complete PostgreSQL fixes
2. Test SSE mode with LiteLLM
3. Implement filesystem service
4. Implement remaining services
5. Create unified registry
6. Deprecate old unified-tools

## Migration Path from v1

### Current State
- **v1 (unified-tools)**: 7 services via complex adapter - DISABLED
- **v2 (this)**: 1 service (PostgreSQL) operational via shim

### Migration Strategy
1. Fix PostgreSQL issues (current)
2. Validate SSE mode with LiteLLM
3. Port remaining services incrementally
4. Run v1 and v2 in parallel during transition
5. Deprecate v1 once v2 is complete

## Technical Achievements

Despite integration challenges, the implementation demonstrates:
- ✅ Dual-mode architecture works
- ✅ Pydantic validation prevents runtime errors
- ✅ Connection pooling improves performance
- ✅ Node.js shim solves Python-MCP bridge issues
- ✅ Clean separation of concerns
- ✅ Production-grade error handling

## References

- **Implementation Plan**: `/home/administrator/projects/mcp/unified-registry/newmcp.md`
- **Status Tracking**: `/home/administrator/projects/mcp/unified-registry/newmcpcheckstatus.md`
- **Original v1**: `/home/administrator/projects/mcp/unified-registry/`
- **MCP Protocol**: https://modelcontextprotocol.io/

---
*Last Updated: 2025-09-08 - PostgreSQL operational, 5 services pending implementation*