# MCP SSE Services Catalog

## Available Services

### 1. PostgreSQL Service (mcp-postgres)
- **Port**: 8001
- **Container**: mcp-postgres
- **Networks**: litellm-net, postgres-net
- **Description**: Database operations and queries

**Tools:**
- `list_databases` - List all databases with optional size information
- `execute_sql` - Execute SQL queries safely
- `list_tables` - List tables in a database
- `table_info` - Get detailed table information
- `query_stats` - Get query performance statistics

### 2. Fetch Service (mcp-fetch)  
- **Port**: 8002
- **Container**: mcp-fetch
- **Networks**: litellm-net
- **Description**: HTTP/web content fetching with markdown conversion

**Tools:**
- `fetch` - Fetch web content and convert to markdown

### 3. Filesystem Service (mcp-filesystem)
- **Port**: 8003
- **Container**: mcp-filesystem  
- **Networks**: litellm-net
- **Description**: Secure file system operations
- **Volumes**: 
  - `/workspace` (read-only)
  - `/shared` (read-write)

**Tools:**
- `read_file` - Read file contents
- `write_file` - Write content to files
- `list_directory` - List directory contents
- `create_directory` - Create directories

### 4. GitHub Service (mcp-github)
- **Port**: 8004
- **Container**: mcp-github
- **Networks**: litellm-net
- **Description**: GitHub API integration

**Tools:**
- `search_repositories` - Search GitHub repositories
- `get_repository` - Get repository details
- `create_issue` - Create GitHub issues

### 5. Monitoring Service (mcp-monitoring)
- **Port**: 8005
- **Container**: mcp-monitoring
- **Networks**: litellm-net
- **Description**: System monitoring and log analysis
- **Volumes**: Docker socket (read-only)

**Tools:**
- `get_container_logs` - Get Docker container logs
- `search_logs` - Search Loki logs  
- `get_system_metrics` - Get system metrics from Netdata

## Service Architecture

```
Internet/LiteLLM
        ↓
    Docker Host
        ↓
   litellm-net (172.x.x.x/16)
        ↓
┌────────────────────────────────────┐
│  MCP SSE Services                  │
│                                    │  
│  ┌─────────┐  ┌─────────┐         │
│  │postgres │  │  fetch  │         │
│  │ :8001   │  │ :8002   │         │
│  └─────────┘  └─────────┘         │
│                                    │
│  ┌──────────┐ ┌────────┐          │
│  │filesystem│ │ github │          │
│  │ :8003    │ │ :8004  │          │
│  └──────────┘ └────────┘          │
│                                    │
│  ┌───────────┐                    │
│  │monitoring │                    │
│  │ :8005     │                    │
│  └───────────┘                    │
└────────────────────────────────────┘
```

## Security Features

- **Network Isolation**: Services isolated on Docker networks
- **Localhost Binding**: All ports bound to 127.0.0.1 only  
- **Input Validation**: Pydantic schemas for all tool inputs
- **File Access Control**: Restricted filesystem paths
- **Non-root Containers**: All services run as unprivileged users
- **Health Checks**: Automatic container health monitoring

## Environment Configuration

All services use environment variables from `/home/administrator/secrets/sse.env`:

- Database credentials
- API keys (GitHub, etc.)
- Service configuration
- File system paths
- Logging levels

## Deployment

Services are deployed using Docker Compose with the master deployment script:

```bash
# Start all services
./deploy.sh up

# Check status
./deploy.sh status

# View logs  
./deploy.sh logs [service]

# Test services
./deploy.sh test [service]

# Stop all services
./deploy.sh down
```

## Integration

Services integrate with:
- **LiteLLM**: Via SSE endpoints for tool execution
- **Open WebUI**: Via LiteLLM bridge
- **Claude Code**: Direct SSE connection possible
- **Custom Clients**: Standard HTTP/SSE API

## Monitoring

Each service provides:
- Health check endpoint (`/health`)
- Service info endpoint (`/info`)  
- Structured JSON logging
- Docker health checks
- Container restart policies