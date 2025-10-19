# TimescaleDB MCP Service

PostgreSQL/TimescaleDB database access service providing database tools via the Model Context Protocol (MCP).

## Overview

This service exposes TimescaleDB database capabilities through MCP, allowing AI assistants to query and analyze time-series data. It connects to the existing TimescaleDB container via the postgres-net network.

## Features

- **SQL Query Execution**: Run complex SELECT, INSERT, UPDATE, DELETE queries
- **Schema Inspection**: Browse tables, columns, indexes, and constraints
- **Time-Series Analysis**: Leverage TimescaleDB's time-series specific functions
- **Data Exploration**: Aggregate queries and statistical analysis
- **Read-Only Security**: Safe database access with write restrictions

## Architecture

- **Base Image**: `crystaldba/postgres-mcp`
- **Database**: TimescaleDB (existing container)
- **Network**: postgres-net (isolated database network)
- **Transport**: SSE (Server-Sent Events) for real-time MCP communication
- **Security**: Read-only access with rate limiting

## Deployment

Deploy using the provided script:
```bash
./deploy.sh
```

This will:
1. Build and start the Docker container
2. Connect to postgres-net network
3. Verify database connectivity
4. Test MCP protocol functionality
5. Update documentation

## Integration

### Codex CLI (Direct SSE)
```bash
codex mcp add timescaledb-direct http://127.0.0.1:48011/sse --transport sse
```

### Claude Code CLI
```bash
claude mcp add timescaledb http://127.0.0.1:48011/sse --transport sse --scope user
```

## API Endpoints

- `GET /sse` - Server-Sent Events for MCP communication
- No HTTP POST endpoints (SSE-only transport)

## Database Configuration

- **Host**: timescaledb (container name on postgres-net)
- **Port**: 5432
- **Database**: timescale
- **User**: tsdbadmin
- **Access**: Read-only (MCP_ALLOW_WRITE=false)
- **Rate Limit**: 100 requests per minute

## Network Architecture

```
Host (127.0.0.1:48011)
    ↓
mcp-timescaledb container (port 8686)
    ↓ postgres-net
TimescaleDB container (port 5432)
```

## Configuration

Environment variables (via `$HOME/projects/secrets/mcp-timescaledb.env`):
- `DATABASE_URI`: PostgreSQL connection string
- `MCP_ALLOW_WRITE`: Set to false for read-only access
- `MCP_RATE_LIMIT`: Request rate limiting (default: 100/min)

## Security Features

- **Read-Only Access**: Write operations disabled
- **Network Isolation**: Runs on dedicated postgres-net
- **Rate Limiting**: Prevents abuse with configurable limits
- **Localhost Binding**: Only accessible from 127.0.0.1
- **Credential Security**: Database credentials stored in secrets

## Tools Available

The service provides PostgreSQL-compatible tools including:
- Query execution and result formatting
- Schema inspection and metadata retrieval
- Time-series specific functions for TimescaleDB
- Data aggregation and statistical analysis
- Database performance monitoring

## Troubleshooting

**Connection Issues**:
```bash
# Check container status
docker ps | grep mcp-timescaledb

# Check database connectivity
docker exec mcp-timescaledb pg_isready -h timescaledb -p 5432 -U tsdbadmin

# Check logs
docker logs mcp-timescaledb
```

**Network Issues**:
```bash
# Verify postgres-net exists
docker network ls | grep postgres-net

# Check network connectivity
docker network inspect postgres-net
```

**SSE Connection**:
```bash
# Test SSE endpoint (should stream events)
curl -i -H "Accept: text/event-stream" http://127.0.0.1:48011/sse
```