# MCP Unified Registry v2 - Dual-Mode Architecture

## Overview

This is the next-generation MCP (Model Context Protocol) implementation featuring a clean dual-mode architecture where each service can operate in both:
- **stdio mode** - For Claude Code integration  
- **SSE mode** - For HTTP/web client integration (LiteLLM, Open WebUI)

## Key Features

### 🔒 Security-First Design
- **Allowlisting only** - No denylists, explicit permission model
- **Path canonicalization** - Prevents directory traversal attacks
- **Read-only mode** - Global flag for safe operation
- **Pydantic validation** - Automatic input validation with descriptive errors

### 🎯 Professional-Grade Architecture
- **Single codebase** per service with dual-mode operation
- **Structured logging** - Service-specific loggers with consistent formatting
- **Connection pooling** - Efficient database resource management
- **Type safety** - Full Pydantic model integration
- **JSON-RPC 2.0** - Strict protocol compliance

### 🚀 Developer Experience
- **Single command deployment** - `./deploy.sh setup` to get started
- **Virtual environment isolation** - Clean dependency management
- **Automatic documentation** - Self-documenting schemas
- **Comprehensive testing** - Built-in test suite

## Quick Start

### 1. Initial Setup
```bash
cd /home/administrator/projects/mcp/unified-registry-v2
./deploy.sh setup
```

### 2. Run PostgreSQL Service

**For Claude Code (stdio mode):**
```bash
./deploy.sh run postgres stdio
```

**For Web Clients (SSE mode):**
```bash
./deploy.sh run postgres sse
# Access at http://localhost:8001
```

### 3. Test the Service
```bash
./deploy.sh test postgres
```

## Architecture

### Directory Structure
```
unified-registry-v2/
├── core/
│   └── mcp_base.py          # Base class for all MCP services
├── services/
│   ├── mcp_postgres.py      # PostgreSQL service
│   ├── postgres_models.py   # Pydantic models
│   └── config/
│       └── postgres.ini     # Service configuration
├── deploy.sh                # Universal deployment script
├── test_stdio.py           # Stdio mode tests
└── README.md               # This file
```

### Service Architecture

Each MCP service inherits from `MCPService` base class which provides:

1. **Dual-mode operation** - stdio/SSE with single codebase
2. **Security features** - Path validation, read-only mode, allowlisting
3. **Pydantic integration** - Automatic parameter validation
4. **JSON-RPC handling** - Protocol-compliant request/response
5. **Structured logging** - Consistent logging across services

## PostgreSQL Service

### Available Tools

1. **list_databases** - List all databases with optional size information
2. **execute_sql** - Execute SQL queries with timeout and format options
3. **list_tables** - List tables in a database with optional sizes
4. **table_info** - Get detailed table information including columns, indexes, constraints
5. **query_stats** - Get query performance statistics from pg_stat_statements

### Configuration

Edit `services/config/postgres.ini`:
```ini
[connection]
host = localhost
port = 5432
database = postgres
user = admin
# Password via DATABASE_URL or DB_PASSWORD env var

[security]
read_only = false
allowed_databases = ["postgres", "mcp_db", "test_db"]
forbidden_operations = ["DROP DATABASE", "TRUNCATE"]
```

### Environment Variables
```bash
export DATABASE_URL=postgresql://user:pass@host:port/database
# OR
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=postgres
export DB_USER=admin
export DB_PASSWORD=secret
```

## Claude Code Integration

Add to `~/.config/claude/mcp_servers.json`:
```json
{
  "postgres-v2": {
    "command": "/home/administrator/projects/mcp/unified-registry-v2/deploy.sh",
    "args": ["run", "postgres", "stdio"],
    "env": {
      "DATABASE_URL": "postgresql://admin:Pass123qp@localhost:5432/postgres"
    }
  }
}
```

## SSE Mode API

When running in SSE mode, the service exposes:

- `GET /health` - Health check endpoint
- `GET /sse` - Server-sent events stream
- `POST /rpc` - JSON-RPC endpoint for tool execution
- `GET /tools` - List available tools
- `GET /docs` - API documentation (when using FastAPI)

## Testing

### Run All Tests
```bash
./deploy.sh test
```

### Test Specific Service
```bash
./deploy.sh test postgres
```

### Manual Testing (stdio mode)
```bash
# Send JSON-RPC requests via stdin
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05"},"id":1}' | \
  python services/mcp_postgres.py --mode stdio
```

### Manual Testing (SSE mode)
```bash
# Start service
./deploy.sh run postgres sse

# In another terminal, test endpoints
curl http://localhost:8001/health
curl http://localhost:8001/tools
```

## Security Features

### Input Validation
All parameters are validated using Pydantic models with:
- Type checking
- Range validation  
- Pattern matching
- Custom validators

### SQL Injection Prevention
- Parameterized queries
- Query validation
- Forbidden operation checking
- Comment stripping

### Path Traversal Prevention
- Path canonicalization
- Allowlist validation
- Restricted file operations

## Deployment Commands

### Setup Environment
```bash
./deploy.sh setup
```

### Run Service
```bash
./deploy.sh run <service> <mode>
# Examples:
./deploy.sh run postgres stdio
./deploy.sh run postgres sse
```

### Check Status
```bash
./deploy.sh status
```

### Clean Up
```bash
./deploy.sh clean
```

## Adding New Services

1. Create Pydantic models in `services/<service>_models.py`
2. Create service class in `services/mcp_<service>.py`
3. Create configuration in `services/config/<service>.ini`
4. Register tools in the service class
5. Test with `./deploy.sh test <service>`

## Advantages Over Previous Architecture

### vs. Unified-Tools Approach
- ✅ **Simpler** - No complex adapter layers
- ✅ **Cleaner** - Single source of truth per service
- ✅ **Flexible** - Easy to add new modes (WebSocket, gRPC)
- ✅ **Maintainable** - One codebase per service

### vs. SSE-Only Approach
- ✅ **Native Claude support** - Direct stdio communication
- ✅ **No middleware needed** - Reduced complexity
- ✅ **Better performance** - No HTTP overhead for Claude
- ✅ **Cost optimized** - Efficient for both use cases

## Implementation Status

- ✅ Base framework with security features
- ✅ PostgreSQL service with 5 tools
- ✅ Pydantic validation models
- ✅ Dual-mode operation (stdio/SSE)
- ✅ Deployment automation
- ✅ Testing infrastructure
- ⏳ Filesystem service
- ⏳ GitHub service
- ⏳ Monitoring service
- ⏳ Production deployment

## Next Steps

1. Implement remaining services (filesystem, github, monitoring)
2. Add WebSocket mode for real-time updates
3. Implement state management backends (Redis, SQLite)
4. Add metrics and observability
5. Create Docker images for containerized deployment

## Contributing

This architecture is designed for extensibility. To add a new service:

1. Inherit from `MCPService` base class
2. Define Pydantic models for parameters
3. Register tools with handlers
4. Add service-specific configuration
5. Test both stdio and SSE modes

## License

This is a private implementation for ai-servicers.com infrastructure.

---
*Built with the MCP Protocol: https://modelcontextprotocol.io/*
*Architecture follows security-first and validate-first principles*