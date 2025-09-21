#!/usr/bin/env python3
"""
PostgreSQL MCP Service with Enhanced Debugging
"""
import sys
import os
import json
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Use debug base instead of regular base
from core.mcp_base_debug import MCPServiceDebug

# Import everything else from regular postgres service
from mcp_postgres import (
    ListDatabasesParams,
    ExecuteSqlParams,
    ListTablesParams,
    TableInfoParams,
    QueryStatsParams
)

class PostgreSQLServiceDebug(MCPServiceDebug):
    """PostgreSQL Service with enhanced debugging"""
    
    def __init__(self, config: dict):
        # Import inside to avoid circular dependency
        from mcp_postgres import PostgreSQLService
        
        # Initialize with debug base
        super().__init__("postgres", "1.0.0", config)
        
        # Copy implementation from regular service
        self.original_service = PostgreSQLService(config)
        
        # Use the original service's connection pool
        self.connection_pool = self.original_service.connection_pool
        
        # Register tools with debugging
        self._register_tools()
    
    def _register_tools(self):
        """Register all PostgreSQL tools with debug logging"""
        tools = [
            ("list_databases", self.list_databases_handler, ListDatabasesParams, False, "List all databases in the PostgreSQL server"),
            ("execute_sql", self.execute_sql_handler, ExecuteSqlParams, False, "Execute SQL queries on the database"),
            ("list_tables", self.list_tables_handler, ListTablesParams, False, "List tables in a database"),
            ("table_info", self.table_info_handler, TableInfoParams, False, "Get detailed information about a table"),
            ("query_stats", self.query_stats_handler, QueryStatsParams, False, "Get query performance statistics")
        ]
        
        for name, handler, schema, write_op, desc in tools:
            self.register_tool(name, handler, schema, write_op, desc)
            self._log_debug("TOOL_REGISTERED", {"name": name, "description": desc})
    
    def get_connection(self):
        """Use original service's connection method"""
        return self.original_service.get_connection()
    
    def list_databases_handler(self, params):
        self._log_debug("HANDLER_START", {"tool": "list_databases", "params": params.model_dump()})
        result = self.original_service.list_databases_handler(params)
        self._log_debug("HANDLER_END", {"tool": "list_databases", "result_count": result.get("count", 0)})
        return result
    
    def execute_sql_handler(self, params):
        self._log_debug("HANDLER_START", {"tool": "execute_sql", "query_length": len(params.query)})
        result = self.original_service.execute_sql_handler(params)
        self._log_debug("HANDLER_END", {"tool": "execute_sql", "has_rows": "rows" in result})
        return result
    
    def list_tables_handler(self, params):
        self._log_debug("HANDLER_START", {"tool": "list_tables", "params": params.model_dump()})
        result = self.original_service.list_tables_handler(params)
        self._log_debug("HANDLER_END", {"tool": "list_tables", "result_count": result.get("count", 0)})
        return result
    
    def table_info_handler(self, params):
        self._log_debug("HANDLER_START", {"tool": "table_info", "table": params.table})
        result = self.original_service.table_info_handler(params)
        self._log_debug("HANDLER_END", {"tool": "table_info", "has_columns": "columns" in result})
        return result
    
    def query_stats_handler(self, params):
        self._log_debug("HANDLER_START", {"tool": "query_stats", "params": params.model_dump()})
        result = self.original_service.query_stats_handler(params)
        self._log_debug("HANDLER_END", {"tool": "query_stats", "has_stats": "stats" in result})
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PostgreSQL MCP Service with Debugging')
    parser.add_argument('--mode', choices=['stdio', 'sse'], default='stdio',
                        help='Run mode: stdio for Claude Code, sse for web clients')
    
    args = parser.parse_args()
    
    # Load configuration
    config = {
        'database': {
            'host': os.environ.get('DB_HOST', 'localhost'),
            'port': os.environ.get('DB_PORT', '5432'),
            'min_connections': 2,
            'max_connections': 10
        }
    }
    
    # Create and run service with debugging
    service = PostgreSQLServiceDebug(config)
    
    if args.mode == 'stdio':
        service.run_stdio_mode()
    else:
        service.run_sse_mode(config)