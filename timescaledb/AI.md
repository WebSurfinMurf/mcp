# TimescaleDB MCP Service Notes

## Service Overview
**Purpose**: Time-series database operations and analytics
**Type**: Custom FastAPI MCP server with TimescaleDB integration
**Port**: 48011
**Network**: postgres-net (connects to TimescaleDB container)

## Core Capabilities
- **Time-Series Queries**: Optimized for temporal data analysis
- **Database Operations**: Schema inspection, query execution
- **TimescaleDB Features**: Hypertables, continuous aggregates, compression
- **Query Analysis**: Execution plan optimization for time-series workloads
- **Health Monitoring**: Database performance and status checks

## Available Tools
1. **`execute_sql(sql)`** - Execute SELECT queries on TimescaleDB
2. **`list_databases()`** - List available databases
3. **`list_schemas()`** - List database schemas
4. **`list_objects(schema, object_type)`** - List tables, views, sequences
5. **`get_object_details(schema, object_name, object_type)`** - Detailed object info
6. **`explain_query(sql, analyze=false)`** - Query execution plan analysis

## Database Connection
- **Host**: timescaledb (via postgres-net)
- **Port**: 5432
- **Database**: timescale
- **User**: tsdbadmin
- **Access Mode**: Read-only for safety
- **Connection Pool**: asyncpg with connection pooling

## TimescaleDB Features
- **Hypertables**: Time-series optimized table structures
- **Continuous Aggregates**: Pre-computed time-based rollups
- **Compression**: Automatic data compression for older data
- **Time Bucketing**: Built-in time-based aggregation functions
- **Retention Policies**: Automated data lifecycle management

## Technical Implementation
- **Framework**: FastAPI with asyncpg database driver
- **Network**: Isolated postgres-net Docker network
- **Environment**: Database credentials via environment variables
- **Error Handling**: Graceful degradation for connection issues
- **Query Safety**: Read-only mode prevents data modification

## Client Registration
**Codex CLI**: `codex mcp add timescaledb python3 /home/administrator/projects/mcp/timescaledb/mcp-bridge.py`
**Claude Code**: `claude mcp add timescaledb http://127.0.0.1:48011/sse --transport sse --scope user`

## Common Use Cases
- Time-series data analysis and reporting
- IoT sensor data queries
- Performance metrics analysis
- Historical data trend analysis
- Real-time monitoring dashboards

## Query Examples
```sql
-- List hypertables
SELECT * FROM timescaledb_information.hypertables;

-- Time-bucketed aggregation
SELECT time_bucket('1 hour', time) as hour, avg(temperature)
FROM sensors GROUP BY hour ORDER BY hour;

-- Recent data analysis
SELECT * FROM metrics WHERE time > NOW() - INTERVAL '24 hours';
```

## Troubleshooting
- **Connection Errors**: Verify TimescaleDB container is running
- **Query Timeouts**: Check query complexity and indexes
- **Permission Denied**: Verify tsdbadmin user permissions
- **Network Issues**: Confirm postgres-net connectivity

## Security Model
- **Read-Only Access**: Prevents accidental data modification
- **Network Isolation**: Limited to postgres-net communication
- **Credential Management**: Environment-based authentication
- **Query Validation**: SQL injection prevention built-in

## Integration Points
- **TimescaleDB Container**: Main data storage
- **postgres-net**: Docker network for database communication
- **Environment File**: `$HOME/projects/secrets/mcp-timescaledb.env`
- **Bridge Script**: `/home/administrator/projects/mcp/timescaledb/mcp-bridge.py`