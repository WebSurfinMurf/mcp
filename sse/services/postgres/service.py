"""
PostgreSQL MCP SSE Service
Provides database operations via Server-Sent Events
"""

import os
import sys
import asyncio
import time
from typing import List, Dict, Any, Optional
import asyncpg
import logging

# Add core to Python path
sys.path.append('/app/core')

from mcp_sse import MCPSSEServer
from models import (
    ListDatabasesInput, ExecuteSqlInput, ListTablesInput, 
    TableInfoInput, QueryStatsInput, DatabaseInfo, TableInfo, 
    ColumnInfo, QueryResult, DatabaseListOutput, SQLExecutionOutput,
    TableListOutput, TableInfoOutput, QueryStatsOutput
)


class PostgreSQLMCPService:
    """PostgreSQL MCP SSE Service Implementation"""
    
    def __init__(self):
        self.logger = logging.getLogger("mcp-postgres")
        self.connection_pool = None
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://admin:Pass123qp@postgres:5432/postgres')
        
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.connection_pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=30,
                server_settings={
                    'application_name': 'mcp-postgres-service'
                }
            )
            self.logger.info("PostgreSQL connection pool initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize connection pool: {e}")
            self.logger.warning("Service will start without database connection - tools will fail until connection is established")
            self.connection_pool = None
    
    async def ensure_connection(self):
        """Ensure database connection is available, try to reconnect if not"""
        if not self.connection_pool:
            try:
                self.logger.info("Attempting to reconnect to database...")
                await self.initialize()
                return self.connection_pool is not None
            except:
                return False
        return True
    
    async def close(self):
        """Close database connections"""
        if self.connection_pool:
            await self.connection_pool.close()
            self.logger.info("PostgreSQL connection pool closed")
    
    async def list_databases(self, include_size: bool = False) -> Dict[str, Any]:
        """List all databases"""
        if not await self.ensure_connection():
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Database connection not available. Please check PostgreSQL server connectivity."
                    }
                ],
                "isError": True
            }
        
        try:
            async with self.connection_pool.acquire() as conn:
                if include_size:
                    query = """
                    SELECT 
                        d.datname as name,
                        pg_catalog.pg_get_userbyid(d.datdba) as owner,
                        pg_catalog.pg_encoding_to_char(d.encoding) as encoding,
                        d.datcollate as collation,
                        pg_catalog.pg_database_size(d.datname) as size_bytes,
                        pg_catalog.pg_size_pretty(pg_catalog.pg_database_size(d.datname)) as size_pretty
                    FROM pg_catalog.pg_database d
                    WHERE d.datistemplate = false
                    ORDER BY d.datname;
                    """
                else:
                    query = """
                    SELECT 
                        d.datname as name,
                        pg_catalog.pg_get_userbyid(d.datdba) as owner,
                        pg_catalog.pg_encoding_to_char(d.encoding) as encoding,
                        d.datcollate as collation
                    FROM pg_catalog.pg_database d
                    WHERE d.datistemplate = false
                    ORDER BY d.datname;
                    """
                
                rows = await conn.fetch(query)
                databases = [dict(row) for row in rows]
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Found {len(databases)} databases:\n\n" + 
                                   "\n".join([
                                       f"• **{db['name']}** (owner: {db['owner']}, encoding: {db['encoding']})" +
                                       (f" - Size: {db['size_pretty']}" if include_size and 'size_pretty' in db else "")
                                       for db in databases
                                   ])
                        }
                    ]
                }
                
        except Exception as e:
            self.logger.error(f"Error listing databases: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error listing databases: {str(e)}"
                    }
                ],
                "isError": True
            }
    
    async def execute_sql(self, query: str, database: str = "postgres", limit: int = 100) -> Dict[str, Any]:
        """Execute SQL query safely"""
        try:
            # Security: Block dangerous operations
            query_lower = query.lower().strip()
            dangerous_keywords = ['drop', 'delete', 'truncate', 'alter', 'create', 'insert', 'update']
            
            # Allow SELECT and some safe operations
            if not query_lower.startswith(('select', 'show', 'explain', 'with')):
                if any(keyword in query_lower for keyword in dangerous_keywords):
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "Error: Only SELECT, SHOW, EXPLAIN, and WITH queries are allowed for security reasons."
                            }
                        ],
                        "isError": True
                    }
            
            # Connect to specific database
            db_url = self.database_url.rsplit('/', 1)[0] + f'/{database}'
            
            start_time = time.time()
            
            async with asyncpg.connect(db_url) as conn:
                # Add LIMIT if not present in SELECT queries
                if query_lower.startswith('select') and 'limit' not in query_lower:
                    query = f"{query.rstrip(';')} LIMIT {limit};"
                
                rows = await conn.fetch(query)
                
                execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                if not rows:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Query executed successfully. No rows returned.\nExecution time: {execution_time:.2f}ms"
                            }
                        ]
                    }
                
                # Get column names
                columns = list(rows[0].keys()) if rows else []
                
                # Convert rows to list of lists for JSON serialization
                row_data = []
                for row in rows:
                    row_list = []
                    for value in row:
                        if value is None:
                            row_list.append(None)
                        else:
                            row_list.append(str(value))
                    row_data.append(row_list)
                
                # Format as table
                result_text = f"Query executed successfully. Found {len(rows)} rows.\n"
                result_text += f"Execution time: {execution_time:.2f}ms\n\n"
                
                if rows:
                    # Create table format
                    result_text += "| " + " | ".join(columns) + " |\n"
                    result_text += "|" + "|".join(["-" * (len(col) + 2) for col in columns]) + "|\n"
                    
                    for row in row_data[:20]:  # Show first 20 rows in formatted output
                        result_text += "| " + " | ".join([str(val) if val is not None else "NULL" for val in row]) + " |\n"
                    
                    if len(rows) > 20:
                        result_text += f"\n... and {len(rows) - 20} more rows"
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": result_text
                        }
                    ]
                }
                
        except Exception as e:
            self.logger.error(f"Error executing SQL: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"SQL execution error: {str(e)}"
                    }
                ],
                "isError": True
            }
    
    async def list_tables(self, database: str = "postgres", schema: str = "public") -> Dict[str, Any]:
        """List tables in a database schema"""
        try:
            db_url = self.database_url.rsplit('/', 1)[0] + f'/{database}'
            
            async with asyncpg.connect(db_url) as conn:
                query = """
                SELECT 
                    t.table_name,
                    t.table_type,
                    pg_relation_size(c.oid) as size_bytes,
                    pg_size_pretty(pg_relation_size(c.oid)) as size_pretty
                FROM information_schema.tables t
                LEFT JOIN pg_class c ON c.relname = t.table_name
                WHERE t.table_schema = $1
                ORDER BY t.table_name;
                """
                
                rows = await conn.fetch(query, schema)
                
                if not rows:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"No tables found in database '{database}', schema '{schema}'"
                            }
                        ]
                    }
                
                result_text = f"Found {len(rows)} tables in database '{database}', schema '{schema}':\n\n"
                
                for row in rows:
                    table_type = "View" if row['table_type'] == 'VIEW' else "Table"
                    size_info = f" ({row['size_pretty']})" if row['size_pretty'] else ""
                    result_text += f"• **{row['table_name']}** - {table_type}{size_info}\n"
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": result_text
                        }
                    ]
                }
                
        except Exception as e:
            self.logger.error(f"Error listing tables: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error listing tables: {str(e)}"
                    }
                ],
                "isError": True
            }
    
    async def table_info(self, table: str, database: str = "postgres", schema: str = "public") -> Dict[str, Any]:
        """Get detailed table information"""
        try:
            db_url = self.database_url.rsplit('/', 1)[0] + f'/{database}'
            
            async with asyncpg.connect(db_url) as conn:
                # Get column information
                columns_query = """
                SELECT 
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    CASE WHEN tc.constraint_type = 'PRIMARY KEY' THEN true ELSE false END as is_primary_key
                FROM information_schema.columns c
                LEFT JOIN information_schema.key_column_usage kcu 
                    ON c.table_name = kcu.table_name 
                    AND c.column_name = kcu.column_name
                    AND c.table_schema = kcu.table_schema
                LEFT JOIN information_schema.table_constraints tc
                    ON kcu.constraint_name = tc.constraint_name
                    AND kcu.table_schema = tc.table_schema
                WHERE c.table_schema = $1 AND c.table_name = $2
                ORDER BY c.ordinal_position;
                """
                
                columns = await conn.fetch(columns_query, schema, table)
                
                if not columns:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Table '{schema}.{table}' not found in database '{database}'"
                            }
                        ],
                        "isError": True
                    }
                
                # Get row count and size
                stats_query = f"""
                SELECT 
                    COUNT(*) as row_count,
                    pg_relation_size('{schema}.{table}') as size_bytes,
                    pg_size_pretty(pg_relation_size('{schema}.{table}')) as size_pretty
                FROM "{schema}"."{table}";
                """
                
                try:
                    stats = await conn.fetchrow(stats_query)
                except:
                    stats = {'row_count': None, 'size_bytes': None, 'size_pretty': None}
                
                # Format result
                result_text = f"**Table Information: {schema}.{table}**\n\n"
                
                if stats['row_count'] is not None:
                    result_text += f"**Rows:** {stats['row_count']:,}\n"
                if stats['size_pretty']:
                    result_text += f"**Size:** {stats['size_pretty']}\n"
                
                result_text += f"\n**Columns ({len(columns)}):**\n\n"
                result_text += "| Column | Type | Nullable | Default | Primary Key |\n"
                result_text += "|--------|------|----------|---------|-------------|\n"
                
                for col in columns:
                    nullable = "Yes" if col['is_nullable'] == 'YES' else "No"
                    default = col['column_default'] or ""
                    pk = "Yes" if col['is_primary_key'] else "No"
                    result_text += f"| {col['column_name']} | {col['data_type']} | {nullable} | {default} | {pk} |\n"
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": result_text
                        }
                    ]
                }
                
        except Exception as e:
            self.logger.error(f"Error getting table info: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error getting table information: {str(e)}"
                    }
                ],
                "isError": True
            }
    
    async def query_stats(self, database: str = "postgres", limit: int = 10) -> Dict[str, Any]:
        """Get query performance statistics"""
        try:
            db_url = self.database_url.rsplit('/', 1)[0] + f'/{database}'
            
            async with asyncpg.connect(db_url) as conn:
                # Check if pg_stat_statements extension is available
                ext_check = """
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                );
                """
                
                has_pg_stat = await conn.fetchval(ext_check)
                
                if not has_pg_stat:
                    # Basic stats without pg_stat_statements
                    basic_stats = """
                    SELECT 
                        schemaname,
                        tablename,
                        seq_scan,
                        seq_tup_read,
                        idx_scan,
                        idx_tup_fetch
                    FROM pg_stat_user_tables 
                    ORDER BY seq_tup_read DESC
                    LIMIT $1;
                    """
                    
                    rows = await conn.fetch(basic_stats, limit)
                    
                    result_text = f"**Database Statistics (Basic) - {database}**\n\n"
                    result_text += "pg_stat_statements extension not available. Showing table access statistics:\n\n"
                    result_text += "| Table | Seq Scans | Seq Reads | Index Scans | Index Reads |\n"
                    result_text += "|-------|-----------|-----------|-------------|-------------|\n"
                    
                    for row in rows:
                        result_text += f"| {row['schemaname']}.{row['tablename']} | {row['seq_scan']} | {row['seq_tup_read']} | {row['idx_scan'] or 0} | {row['idx_tup_fetch'] or 0} |\n"
                
                else:
                    # Advanced stats with pg_stat_statements
                    query_stats = """
                    SELECT 
                        substring(query, 1, 60) as query_short,
                        calls,
                        total_exec_time / calls as avg_time_ms,
                        total_exec_time,
                        rows
                    FROM pg_stat_statements 
                    WHERE query NOT LIKE '%pg_stat_statements%'
                    ORDER BY total_exec_time DESC
                    LIMIT $1;
                    """
                    
                    rows = await conn.fetch(query_stats, limit)
                    
                    result_text = f"**Query Performance Statistics - {database}**\n\n"
                    result_text += f"Top {len(rows)} queries by total execution time:\n\n"
                    result_text += "| Query (truncated) | Calls | Avg Time (ms) | Total Time | Rows |\n"
                    result_text += "|-------------------|-------|---------------|------------|------|\n"
                    
                    for row in rows:
                        query_short = row['query_short'].replace('\n', ' ').replace('|', '\\|')
                        avg_time = f"{row['avg_time_ms']:.2f}" if row['avg_time_ms'] else "0"
                        total_time = f"{row['total_exec_time']:.2f}" if row['total_exec_time'] else "0"
                        result_text += f"| {query_short}... | {row['calls']} | {avg_time} | {total_time} | {row['rows']} |\n"
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": result_text
                        }
                    ]
                }
                
        except Exception as e:
            self.logger.error(f"Error getting query stats: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error getting query statistics: {str(e)}"
                    }
                ],
                "isError": True
            }


async def main():
    """Main entry point"""
    # Get configuration from environment
    service_port = int(os.getenv('SERVICE_PORT', '8001'))
    
    # Create PostgreSQL service
    pg_service = PostgreSQLMCPService()
    await pg_service.initialize()
    
    # Create SSE server
    server = MCPSSEServer(
        name="postgres",
        version="1.0.0",
        port=service_port
    )
    
    # Register tools with MCP 2025-06-18 output schemas
    server.register_tool(
        "list_databases",
        pg_service.list_databases,
        ListDatabasesInput,
        "List all databases with optional size information",
        DatabaseListOutput
    )
    
    server.register_tool(
        "execute_sql",
        pg_service.execute_sql,
        ExecuteSqlInput,
        "Execute SQL queries safely (SELECT, SHOW, EXPLAIN, WITH only)",
        SQLExecutionOutput
    )
    
    server.register_tool(
        "list_tables",
        pg_service.list_tables,
        ListTablesInput,
        "List tables in a database schema",
        TableListOutput
    )
    
    server.register_tool(
        "table_info",
        pg_service.table_info,
        TableInfoInput,
        "Get detailed information about a table including columns and statistics",
        TableInfoOutput
    )
    
    server.register_tool(
        "query_stats",
        pg_service.query_stats,
        QueryStatsInput,
        "Get query performance statistics for the database",
        QueryStatsOutput
    )
    
    try:
        # Start the server
        await server.run_async()
    finally:
        # Clean up
        await pg_service.close()


if __name__ == "__main__":
    asyncio.run(main())