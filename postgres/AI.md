# PostgreSQL MCP Service Notes

## Service Overview
**Purpose**: General-purpose PostgreSQL database operations and analysis
**Type**: Direct postgres-mcp package execution (stdio mode)
**Port**: N/A (stdio transport, no network port)
**Network**: Host network (connects to localhost:5432)

## Core Capabilities
- **Query Execution**: Safe SELECT, SHOW, and schema queries
- **Database Health Analysis**: Comprehensive performance monitoring
- **Index Optimization**: Query analysis and index recommendations
- **Query Planning**: Execution plan analysis with cost estimates
- **Workload Analysis**: Analyze frequently executed queries

## Available Tools
1. **`execute_sql(sql)`** - Execute SELECT queries safely (read-only mode)
2. **`analyze_db_health()`** - Comprehensive database health analysis
3. **`analyze_query_indexes(queries)`** - Analyze up to 10 queries for optimal indexes
4. **`analyze_workload_indexes()`** - Analyze workload and recommend indexes
5. **`explain_query(sql, analyze=false, hypothetical_indexes=[])`** - Query execution plan with cost analysis

## Database Connection
- **Host**: localhost (main PostgreSQL instance)
- **Port**: 5432
- **Database**: postgres (default database)
- **User**: admin
- **Access Mode**: Restricted (read-only for safety)
- **Connection Pool**: Managed by postgres-mcp package

## Advanced Features
- **Index Tuning**: Industrial-strength Anytime Algorithm for index optimization
- **Query Analysis**: Real execution statistics and cost estimates
- **Health Checks**: Systematic identification of performance issues
- **Hypothetical Indexes**: Test index effectiveness without creating them
- **Workload Analysis**: Analyze pg_stat_statements for optimization

## Technical Implementation
- **Package**: crystaldba/postgres-mcp (official package)
- **Transport**: stdio (direct process communication)
- **Runner**: Custom Python wrapper script
- **Authentication**: Database connection string
- **Error Handling**: Graceful connection failure handling

## Client Registration
**Codex CLI**: `codex mcp add postgres python3 /home/administrator/projects/mcp/postgres/postgres-mcp-stdio.py`
**Claude Code**: `claude mcp add postgres-direct http://127.0.0.1:48010/sse --transport sse --scope user` (separate SSE service)

## Database Coverage
The main PostgreSQL instance contains multiple application databases:
- **Application DBs**: CODEXCHEATED-lite_db_standalone, guacamole_db, n8n_db, nextcloud, etc.
- **System DBs**: postgres, template0, template1
- **MCP DBs**: mcp_memory, mcp_memory_admin, mcp_memory_administrator
- **Service DBs**: openbao_db, openproject_production, postfixadmin

## Common Use Cases
- **Database Performance Tuning**: Identify slow queries and optimization opportunities
- **Schema Analysis**: Explore database structure and relationships
- **Query Optimization**: Analyze and improve SQL query performance
- **Health Monitoring**: Regular database health assessments
- **Index Planning**: Determine optimal indexing strategies

## Query Safety
- **Read-Only Mode**: Prevents accidental data modification
- **Query Validation**: Only SELECT, SHOW, and schema queries allowed
- **Connection Limits**: Controlled connection pool usage
- **Timeout Protection**: Prevents long-running query issues
- **SQL Injection Prevention**: Parameterized query support

## Performance Analysis
- **Execution Plans**: Detailed EXPLAIN output with costs
- **Index Usage**: Analysis of existing index effectiveness
- **Table Statistics**: Row counts, sizes, and access patterns
- **Query Performance**: Execution time and resource usage
- **Bottleneck Identification**: I/O, CPU, and memory constraints

## Troubleshooting
- **Connection Refused**: Verify PostgreSQL is running on localhost:5432
- **Authentication Failed**: Check admin user credentials
- **Query Timeout**: Reduce query complexity or increase timeout
- **Permission Denied**: Verify admin user has required privileges
- **Module Not Found**: Ensure postgres-mcp package is installed

## Security Model
- **Restricted Access**: Read-only mode prevents data modification
- **Local Connection**: Only connects to localhost PostgreSQL
- **Credential Security**: Database passwords in environment/config
- **Query Filtering**: Blocks potentially harmful SQL statements

## Package Management
- **Installation**: `pip3 install postgres-mcp --break-system-packages`
- **Version**: postgres-mcp>=0.3.0
- **Dependencies**: asyncpg, pydantic, typer, humanize
- **Updates**: Regular package updates for security and features

## Integration Points
- **Main PostgreSQL**: Primary database instance (postgres:5432)
- **stdio Transport**: Direct process communication
- **Runner Script**: `/home/administrator/projects/mcp/postgres/postgres-mcp-stdio.py`
- **Environment**: DATABASE_URL configuration
- **Health Endpoint**: N/A (stdio mode, no HTTP endpoints)