"""
Modern PostgreSQL Tools for Centralized MCP Server
Based on call518/MCP-PostgreSQL-Ops with compatibility for PostgreSQL 15.13

Features:
- Modern async PostgreSQL operations using asyncpg
- Compatible with PostgreSQL 12-17
- Production-safe read-only operations
- Zero configuration with automatic version detection
"""

import asyncpg
import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

# Logger configuration
logger = logging.getLogger(__name__)

# PostgreSQL connection configuration
POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "user": os.getenv("POSTGRES_USER", "admin"),
    "password": os.getenv("POSTGRES_PASSWORD", "Pass123qp"),
    "database": os.getenv("POSTGRES_DB", "postgres"),
}

async def get_db_connection(database: str = None) -> asyncpg.Connection:
    """Create PostgreSQL database connection.

    Args:
        database: Database name to connect to. If None, uses default from config.
    """
    try:
        config = POSTGRES_CONFIG.copy()
        if database:
            config["database"] = database

        conn = await asyncpg.connect(**config)
        logger.debug(f"Connected to PostgreSQL at {config['host']}:{config['port']}/{config['database']}")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        raise

async def execute_query(query: str, params: Optional[List] = None, database: str = None) -> List[Dict[str, Any]]:
    """Execute query and return results as list of dictionaries.

    Args:
        query: SQL query to execute
        params: Query parameters
        database: Database name to connect to. If None, uses default from config.
    """
    conn = None
    try:
        conn = await get_db_connection(database)
        if params:
            rows = await conn.fetch(query, *params)
        else:
            rows = await conn.fetch(query)

        # Convert Record to Dict with JSON serialization support
        result = []
        for row in rows:
            row_dict = {}
            for key, value in dict(row).items():
                # Handle special PostgreSQL types
                if hasattr(value, 'isoformat'):  # datetime objects
                    row_dict[key] = value.isoformat()
                elif isinstance(value, (list, dict)):  # arrays and JSON
                    row_dict[key] = json.dumps(value) if isinstance(value, dict) else value
                else:
                    row_dict[key] = value
            result.append(row_dict)

        logger.debug(f"Query executed successfully, returned {len(result)} rows")
        return result

    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        logger.debug(f"Failed query: {query}")
        raise
    finally:
        if conn:
            await conn.close()

async def execute_single_query(query: str, params: Optional[List] = None, database: str = None) -> Optional[Dict[str, Any]]:
    """Execute query that returns a single result."""
    results = await execute_query(query, params, database)
    return results[0] if results else None

def format_table_data(data: List[Dict[str, Any]], max_width: int = 100) -> str:
    """Format query results as a readable table."""
    if not data:
        return "No data found."

    # Get column names
    columns = list(data[0].keys())

    # Calculate column widths
    col_widths = {}
    for col in columns:
        col_widths[col] = min(max_width, max(len(str(col)), max(len(str(row.get(col, ''))) for row in data)))

    # Create header
    header = " | ".join(col.ljust(col_widths[col]) for col in columns)
    separator = "-" * len(header)

    # Create rows
    rows = []
    for row in data:
        formatted_row = " | ".join(str(row.get(col, '')).ljust(col_widths[col]) for col in columns)
        rows.append(formatted_row)

    return f"{header}\n{separator}\n" + "\n".join(rows)

async def get_postgresql_version() -> str:
    """Get PostgreSQL server version information."""
    try:
        query = """
        SELECT version() as version_info,
               current_setting('server_version') as version_number,
               current_setting('server_version_num') as version_num
        """
        result = await execute_single_query(query)
        return result if result else {"error": "Unable to retrieve version"}
    except Exception as e:
        return {"error": str(e)}

# Modern PostgreSQL Tools - LangChain Compatible
def run_async_query(coro):
    """Helper to run async queries in sync context for LangChain tools."""
    loop = None
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # If we're already in an async context, create a new event loop in a thread
        import concurrent.futures
        import threading

        def run_in_thread():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()
    else:
        # We can use the current loop or create a new one
        if loop is None:
            return asyncio.run(coro)
        else:
            return loop.run_until_complete(coro)

async def postgres_list_databases_modern() -> str:
    """List all databases with modern PostgreSQL compatibility."""
    try:
        # Modern query that works with PostgreSQL 12-17
        query = """
        SELECT
            d.datname as database_name,
            r.rolname as owner,
            pg_encoding_to_char(d.encoding) as encoding,
            d.datcollate as collation,
            d.datctype as ctype,
            pg_size_pretty(pg_database_size(d.datname)) as size,
            d.datallowconn as allow_connections,
            d.datconnlimit as connection_limit,
            obj_description(d.oid, 'pg_database') as description
        FROM pg_database d
        LEFT JOIN pg_roles r ON d.datdba = r.oid
        WHERE d.datallowconn = true
        ORDER BY d.datname
        """

        result = await execute_query(query)

        if not result:
            return "No accessible databases found."

        return f"Found {len(result)} accessible databases:\n\n" + format_table_data(result)

    except Exception as e:
        logger.error(f"Failed to list databases: {e}")
        return f"Error listing databases: {str(e)}"

async def postgres_list_tables_modern(database_name: str = None, schema_name: str = "public") -> str:
    """List tables in specified database and schema."""
    try:
        query = """
        SELECT
            schemaname as schema_name,
            tablename as table_name,
            tableowner as owner,
            hasindexes as has_indexes,
            hasrules as has_rules,
            hastriggers as has_triggers,
            rowsecurity as row_security
        FROM pg_tables
        WHERE schemaname = $1
        ORDER BY schemaname, tablename
        """

        result = await execute_query(query, [schema_name], database=database_name)

        if not result:
            return f"No tables found in schema '{schema_name}'" + (f" of database '{database_name}'" if database_name else "")

        db_info = f" in database '{database_name}'" if database_name else ""
        return f"Found {len(result)} tables in schema '{schema_name}'{db_info}:\n\n" + format_table_data(result)

    except Exception as e:
        logger.error(f"Failed to list tables: {e}")
        return f"Error listing tables: {str(e)}"

async def postgres_query_advanced(query: str, database_name: str = None) -> str:
    """Execute advanced PostgreSQL query with enhanced security and formatting."""
    try:
        # Enhanced security: block more dangerous operations
        dangerous_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
            'TRUNCATE', 'GRANT', 'REVOKE', 'COPY', 'VACUUM', 'ANALYZE',
            'REINDEX', 'CLUSTER', 'LOCK', 'UNLOCK', 'SET', 'RESET'
        ]

        query_upper = query.upper().strip()
        if any(keyword in query_upper for keyword in dangerous_keywords):
            return "Error: Only read-only SELECT queries are allowed for security."

        # Ensure it's a SELECT statement
        if not query_upper.startswith('SELECT') and not query_upper.startswith('WITH'):
            return "Error: Only SELECT and WITH statements are allowed."

        result = await execute_query(query, database=database_name)

        if not result:
            return "Query executed successfully but returned no results."

        db_info = f" (Database: {database_name})" if database_name else ""
        return f"Query Results{db_info}:\n{len(result)} rows returned\n\n" + format_table_data(result)

    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        return f"Query error: {str(e)}"

async def postgres_server_info() -> str:
    """Get comprehensive PostgreSQL server information."""
    try:
        query = """
        SELECT
            version() as version_info,
            current_setting('server_version') as version,
            current_setting('port') as port,
            current_database() as current_db,
            current_user as current_user,
            session_user as session_user,
            inet_server_addr() as server_address,
            inet_server_port() as server_port,
            pg_postmaster_start_time() as server_start_time,
            current_setting('max_connections') as max_connections,
            (SELECT count(*) FROM pg_stat_activity) as current_connections,
            current_setting('shared_buffers') as shared_buffers,
            current_setting('work_mem') as work_mem,
            current_setting('maintenance_work_mem') as maintenance_work_mem
        """

        result = await execute_single_query(query)

        if not result:
            return "Unable to retrieve server information."

        # Format for better readability
        info = []
        for key, value in result.items():
            info.append(f"{key.replace('_', ' ').title()}: {value}")

        return "PostgreSQL Server Information:\n\n" + "\n".join(info)

    except Exception as e:
        logger.error(f"Failed to get server info: {e}")
        return f"Error retrieving server info: {str(e)}"

async def postgres_database_sizes() -> str:
    """Get database sizes and statistics."""
    try:
        query = """
        SELECT
            datname as database_name,
            pg_size_pretty(pg_database_size(datname)) as size,
            pg_database_size(datname) as size_bytes,
            (SELECT count(*) FROM pg_stat_activity WHERE datname = d.datname) as connections
        FROM pg_database d
        WHERE datallowconn = true
        ORDER BY pg_database_size(datname) DESC
        """

        result = await execute_query(query)

        if not result:
            return "No database size information available."

        return f"Database Sizes ({len(result)} databases):\n\n" + format_table_data(result)

    except Exception as e:
        logger.error(f"Failed to get database sizes: {e}")
        return f"Error retrieving database sizes: {str(e)}"