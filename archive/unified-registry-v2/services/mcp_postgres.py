#!/usr/bin/env python3
"""
PostgreSQL MCP Service
Provides database operations with dual-mode support (stdio/SSE)
"""

import sys
import os
import json
import argparse
import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List, Optional
from contextlib import contextmanager
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.mcp_base import MCPService
from services.postgres_models import (
    ExecuteSqlParams,
    ListDatabasesParams,
    ListTablesParams,
    TableInfoParams,
    QueryStatsParams
)


class PostgreSQLService(MCPService):
    """PostgreSQL MCP service implementation"""
    
    def __init__(self, config_path: Optional[str] = None):
        super().__init__("postgres", "1.0.0", config_path)
        
        # Initialize connection pool
        self.connection_pool = None
        self._init_connection_pool()
        
        # Register tools
        self._register_tools()
    
    def _init_connection_pool(self):
        """Initialize PostgreSQL connection pool"""
        try:
            # Get connection parameters from environment or config
            db_config = self.config.get('connection', {})
            
            # Use DATABASE_URL if available, otherwise build from components
            database_url = os.environ.get('DATABASE_URL')
            if database_url:
                self.logger.info("Using DATABASE_URL from environment")
                # Parse DATABASE_URL
                import urllib.parse
                parsed = urllib.parse.urlparse(database_url)
                connection_params = {
                    'host': parsed.hostname,
                    'port': parsed.port or 5432,
                    'database': parsed.path[1:] if parsed.path else 'postgres',
                    'user': parsed.username,
                    'password': parsed.password
                }
            else:
                connection_params = {
                    'host': db_config.get('host', os.environ.get('DB_HOST', 'localhost')),
                    'port': int(db_config.get('port', os.environ.get('DB_PORT', 5432))),
                    'database': db_config.get('database', os.environ.get('DB_NAME', 'postgres')),
                    'user': db_config.get('user', os.environ.get('DB_USER', 'postgres')),
                    'password': db_config.get('password', os.environ.get('DB_PASSWORD', ''))
                }
            
            # Create connection pool
            min_conn = int(db_config.get('min_connections', 1))
            max_conn = int(db_config.get('max_connections', 10))
            
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                min_conn,
                max_conn,
                **connection_params
            )
            
            self.logger.info(f"Connection pool initialized with {min_conn}-{max_conn} connections")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    def _register_tools(self):
        """Register all PostgreSQL tools"""
        self.register_tool(
            "list_databases",
            self.list_databases_handler,
            ListDatabasesParams,
            write_operation=False,
            description="List all databases in the PostgreSQL server"
        )
        
        self.register_tool(
            "execute_sql",
            self.execute_sql_handler,
            ExecuteSqlParams,
            write_operation=False,  # Will be determined by query type
            description="Execute SQL queries on the database"
        )
        
        self.register_tool(
            "list_tables",
            self.list_tables_handler,
            ListTablesParams,
            write_operation=False,
            description="List tables in a database"
        )
        
        self.register_tool(
            "table_info",
            self.table_info_handler,
            TableInfoParams,
            write_operation=False,
            description="Get detailed information about a table"
        )
        
        self.register_tool(
            "query_stats",
            self.query_stats_handler,
            QueryStatsParams,
            write_operation=False,
            description="Get query performance statistics"
        )
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def list_databases_handler(self, params: ListDatabasesParams) -> Dict[str, Any]:
        """List all databases"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Build query
                query = """
                    SELECT 
                        datname as name,
                        pg_catalog.pg_get_userbyid(datdba) as owner,
                        pg_catalog.pg_encoding_to_char(encoding) as encoding,
                        datcollate as collation,
                        datctype as ctype,
                        pg_catalog.array_to_string(datacl, ', ') as access_privileges
                """
                
                if params.include_size:
                    query += """,
                        pg_database_size(datname) as size,
                        pg_size_pretty(pg_database_size(datname)) as size_pretty
                    """
                
                query += " FROM pg_database"
                
                # Add filters
                conditions = []
                if not params.include_system:
                    conditions.append("datname NOT IN ('postgres', 'template0', 'template1')")
                
                if params.pattern:
                    conditions.append(f"datname LIKE '{params.pattern}'")
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY datname"
                
                cursor.execute(query)
                databases = cursor.fetchall()
                
                return {
                    "databases": databases,
                    "count": len(databases)
                }
    
    def execute_sql_handler(self, params: ExecuteSqlParams) -> Dict[str, Any]:
        """Execute SQL query"""
        # Determine if this is a write operation
        query_upper = params.query.upper().strip()
        is_write = any(query_upper.startswith(op) for op in ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'])
        
        # Check read-only mode for write operations
        if self.read_only and is_write:
            raise PermissionError("Write operations are not allowed in read-only mode")
        
        with self.get_connection() as conn:
            # Switch database if specified
            if params.database and params.database != 'postgres':
                conn.close()
                # Create new connection to specified database
                # This is a simplified approach - in production, you'd manage separate pools
                db_config = {
                    'host': os.environ.get('DB_HOST', 'localhost'),
                    'port': os.environ.get('DB_PORT', 5432),
                    'database': params.database,
                    'user': os.environ.get('DB_USER', 'postgres'),
                    'password': os.environ.get('DB_PASSWORD', '')
                }
                conn = psycopg2.connect(**db_config)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Set statement timeout
                cursor.execute(f"SET statement_timeout = '{params.timeout * 1000}'")
                
                # Execute query
                cursor.execute(params.query)
                
                # Get results based on query type
                if query_upper.startswith('SELECT') or query_upper.startswith('WITH'):
                    rows = cursor.fetchall()
                    
                    # Format results based on requested format
                    if params.format == 'json':
                        result = {
                            "rows": rows,
                            "rowCount": len(rows),
                            "columns": [desc[0] for desc in cursor.description] if cursor.description else []
                        }
                    elif params.format == 'table':
                        # Simple table format
                        if rows and cursor.description:
                            headers = [desc[0] for desc in cursor.description]
                            table_str = self._format_as_table(headers, rows)
                            result = {"table": table_str, "rowCount": len(rows)}
                        else:
                            result = {"table": "No results", "rowCount": 0}
                    else:  # CSV
                        if rows and cursor.description:
                            import csv
                            import io
                            output = io.StringIO()
                            writer = csv.DictWriter(output, fieldnames=[desc[0] for desc in cursor.description])
                            writer.writeheader()
                            writer.writerows(rows)
                            result = {"csv": output.getvalue(), "rowCount": len(rows)}
                        else:
                            result = {"csv": "", "rowCount": 0}
                else:
                    # For INSERT/UPDATE/DELETE, get affected rows
                    result = {
                        "rowsAffected": cursor.rowcount,
                        "statusMessage": cursor.statusmessage
                    }
                
                return result
    
    def list_tables_handler(self, params: ListTablesParams) -> Dict[str, Any]:
        """List tables in a database"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Build query
                query = """
                    SELECT 
                        schemaname as schema,
                        tablename as name,
                        tableowner as owner,
                        hasindexes as has_indexes,
                        hasrules as has_rules,
                        hastriggers as has_triggers
                """
                
                if params.include_sizes:
                    query += """,
                        pg_total_relation_size(schemaname||'.'||tablename) as size,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size_pretty
                    """
                
                query += " FROM pg_tables"
                
                # Add filters
                conditions = [f"schemaname = '{params.schema_name}'"]
                
                if not params.include_system:
                    conditions.append("schemaname NOT IN ('pg_catalog', 'information_schema')")
                
                if params.pattern:
                    conditions.append(f"tablename LIKE '{params.pattern}'")
                
                query += " WHERE " + " AND ".join(conditions)
                query += " ORDER BY schemaname, tablename"
                
                cursor.execute(query)
                tables = cursor.fetchall()
                
                return {
                    "tables": tables,
                    "count": len(tables),
                    "schema": params.schema_name
                }
    
    def table_info_handler(self, params: TableInfoParams) -> Dict[str, Any]:
        """Get detailed table information"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get column information
                cursor.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        character_maximum_length,
                        is_nullable,
                        column_default,
                        ordinal_position
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (params.schema_name, params.table))
                
                columns = cursor.fetchall()
                
                result = {
                    "table": params.table,
                    "schema": params.schema_name,
                    "columns": columns
                }
                
                # Get indexes if requested
                if params.include_indexes:
                    cursor.execute("""
                        SELECT 
                            indexname,
                            indexdef,
                            tablespace
                        FROM pg_indexes
                        WHERE schemaname = %s AND tablename = %s
                    """, (params.schema_name, params.table))
                    
                    result["indexes"] = cursor.fetchall()
                
                # Get constraints if requested
                if params.include_constraints:
                    cursor.execute("""
                        SELECT 
                            conname as name,
                            contype as type,
                            pg_get_constraintdef(c.oid) as definition
                        FROM pg_constraint c
                        JOIN pg_namespace n ON n.oid = c.connamespace
                        JOIN pg_class cl ON cl.oid = c.conrelid
                        WHERE n.nspname = %s AND cl.relname = %s
                    """, (params.schema_name, params.table))
                    
                    result["constraints"] = cursor.fetchall()
                
                # Get statistics if requested
                if params.include_stats:
                    cursor.execute("""
                        SELECT 
                            n_live_tup as live_rows,
                            n_dead_tup as dead_rows,
                            last_vacuum,
                            last_autovacuum,
                            last_analyze,
                            last_autoanalyze
                        FROM pg_stat_user_tables
                        WHERE schemaname = %s AND relname = %s
                    """, (params.schema_name, params.table))
                    
                    stats = cursor.fetchone()
                    if stats:
                        result["statistics"] = stats
                
                return result
    
    def query_stats_handler(self, params: QueryStatsParams) -> Dict[str, Any]:
        """Get query performance statistics from pg_stat_statements"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Check if pg_stat_statements is available
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                    )
                """)
                
                if not cursor.fetchone()['exists']:
                    return {
                        "error": "pg_stat_statements extension is not installed",
                        "hint": "Run 'CREATE EXTENSION pg_stat_statements' as superuser"
                    }
                
                # Build query for statistics
                query = """
                    SELECT 
                        query,
                        calls,
                        total_exec_time as total_time,
                        mean_exec_time as mean_time,
                        max_exec_time as max_time,
                        rows,
                        100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                    FROM pg_stat_statements
                    WHERE calls >= %s
                """
                
                if params.database:
                    query += f" AND dbid = (SELECT oid FROM pg_database WHERE datname = '{params.database}')"
                
                query += f" ORDER BY {params.order_by} DESC LIMIT %s"
                
                cursor.execute(query, (params.min_calls, params.limit))
                stats = cursor.fetchall()
                
                return {
                    "statistics": stats,
                    "count": len(stats),
                    "order_by": params.order_by
                }
    
    def _format_as_table(self, headers: List[str], rows: List[Dict]) -> str:
        """Format query results as a simple ASCII table"""
        if not rows:
            return "No results"
        
        # Calculate column widths
        widths = {h: len(h) for h in headers}
        for row in rows:
            for h in headers:
                if row.get(h) is not None:
                    widths[h] = max(widths[h], len(str(row[h])))
        
        # Build table
        lines = []
        
        # Header
        header_line = " | ".join(h.ljust(widths[h]) for h in headers)
        lines.append(header_line)
        lines.append("-" * len(header_line))
        
        # Rows
        for row in rows:
            row_line = " | ".join(
                str(row.get(h, "")).ljust(widths[h]) for h in headers
            )
            lines.append(row_line)
        
        return "\n".join(lines)
    
    def __del__(self):
        """Cleanup connection pool on exit"""
        if hasattr(self, 'connection_pool') and self.connection_pool:
            self.connection_pool.closeall()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PostgreSQL MCP Service")
    parser.add_argument("--mode", choices=["stdio", "sse"], default="stdio",
                        help="Run mode: stdio for Claude Code, sse for web clients")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    
    args = parser.parse_args()
    
    # Create and run service
    service = PostgreSQLService(args.config)
    service.run(args.mode)


if __name__ == "__main__":
    main()