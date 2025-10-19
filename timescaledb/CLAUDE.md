# Claude Code MCP Integration

This service provides PostgreSQL/TimescaleDB database tools for Claude Code CLI via the Model Context Protocol (MCP).

## Configuration

Add this to your Claude Code MCP configuration:

```bash
claude mcp add timescaledb http://127.0.0.1:48011/sse --transport sse --scope user
```

## Available Tools

This service provides PostgreSQL-compatible database tools including:
- **Query execution**: Run SELECT, INSERT, UPDATE, DELETE queries
- **Schema inspection**: List tables, columns, indexes
- **Data analysis**: Aggregate queries and data exploration
- **TimescaleDB features**: Time-series specific functions and hypertables

## Service Details

- **Container**: mcp-timescaledb
- **Port**: 127.0.0.1:48011
- **SSE Endpoint**: http://127.0.0.1:48011/sse
- **Network**: postgres-net (connects to TimescaleDB)
- **Database**: TimescaleDB (tsdbadmin user, read-only)
- **Environment**: $HOME/projects/secrets/mcp-timescaledb.env

## Database Connection

- **Host**: timescaledb (via postgres-net)
- **Port**: 5432
- **Database**: timescale
- **User**: tsdbadmin (read-only access)
- **Connection**: Secured within docker network

## Example Usage

Query time-series data:
```
Show me the latest 10 records from the sensors table
```

Analyze database schema:
```
List all tables in the timescale database
```

Aggregate time-series data:
```
Calculate average temperature by hour for the last 24 hours
```

## Security

- Read-only database access configured
- Network isolated to postgres-net
- No external network exposure
- Rate limiting enabled (100 req/min)