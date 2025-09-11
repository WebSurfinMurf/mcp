# MCP SSE Services

**Project**: Server-Sent Events (SSE) only MCP services for web integration  
**Location**: `/home/administrator/projects/mcp/sse/`  
**Status**: Phase 1 Implementation  

## Quick Start

```bash
# Deploy all services
./deploy.sh up

# Check status
./deploy.sh status

# View logs
./deploy.sh logs

# Test a service
./deploy.sh test postgres

# Stop all services
./deploy.sh down
```

## Architecture

SSE-only MCP services running in Docker containers on `litellm-net` network:

- **mcp-postgres** (port 8001) - PostgreSQL database operations
- **mcp-fetch** (port 8002) - HTTP/web content fetching  
- **mcp-filesystem** (port 8003) - File system operations
- **mcp-github** (port 8004) - GitHub API integration
- **mcp-monitoring** (port 8005) - System monitoring and logs

## Services

### PostgreSQL Service
- **Endpoint**: http://localhost:8001/sse
- **Tools**: list_databases, execute_sql, list_tables, table_info, query_stats

### Fetch Service  
- **Endpoint**: http://localhost:8002/sse
- **Tools**: fetch (HTTP requests with markdown conversion)

### Filesystem Service
- **Endpoint**: http://localhost:8003/sse  
- **Tools**: read_file, write_file, list_directory, create_directory

### GitHub Service
- **Endpoint**: http://localhost:8004/sse
- **Tools**: search_repositories, get_repository, create_issue

### Monitoring Service
- **Endpoint**: http://localhost:8005/sse
- **Tools**: get_container_logs, search_logs, get_system_metrics

## Configuration

All sensitive configuration is stored in `/home/administrator/secrets/sse.env`

## Documentation

- `docs/API.md` - API documentation
- `docs/SERVICES.md` - Service catalog  
- `docs/INTEGRATION.md` - Integration guide
- `finalplan.md` - Complete implementation plan

---
*SSE-only MCP architecture for simplified web integration*