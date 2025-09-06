#!/usr/bin/env python3
"""
MCP Server for TimescaleDB
Provides time-series specific database operations
"""

import os
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import asyncpg
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration from environment
DB_CONFIG = {
    "host": os.getenv("TSDB_HOST", "localhost"),
    "port": int(os.getenv("TSDB_PORT", "5432")),
    "database": os.getenv("TSDB_DATABASE", "postgres"),
    "user": os.getenv("TSDB_USER"),
    "password": os.getenv("TSDB_PASSWORD"),
}

class TimescaleDBServer:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                **DB_CONFIG,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("Connected to TimescaleDB")
        except Exception as e:
            logger.error(f"Failed to connect to TimescaleDB: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup database connections"""
        if self.pool:
            await self.pool.close()
    
    async def execute_query(self, query: str, params: List[Any] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dicts"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *(params or []))
            return [dict(row) for row in rows]
    
    async def execute_command(self, command: str, params: List[Any] = None) -> str:
        """Execute a command and return status message"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(command, *(params or []))
            return result

# Create server instance
tsdb_server = TimescaleDBServer()
server = Server("mcp-timescaledb")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available TimescaleDB tools"""
    return [
        Tool(
            name="tsdb_query",
            description="Execute a SELECT query on TimescaleDB",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL SELECT query to execute"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="tsdb_execute",
            description="Execute a non-SELECT SQL command (INSERT, UPDATE, DELETE, CREATE, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "SQL command to execute"
                    }
                },
                "required": ["command"]
            }
        ),
        Tool(
            name="tsdb_create_hypertable",
            description="Convert a regular table to a TimescaleDB hypertable",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table to convert"
                    },
                    "time_column": {
                        "type": "string",
                        "description": "Name of the time column",
                        "default": "time"
                    },
                    "chunk_time_interval": {
                        "type": "string",
                        "description": "Chunk time interval (e.g., '1 day', '1 week')",
                        "default": "1 week"
                    }
                },
                "required": ["table_name"]
            }
        ),
        Tool(
            name="tsdb_show_hypertables",
            description="List all hypertables in the database",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="tsdb_show_chunks",
            description="Show chunks for a specific hypertable",
            inputSchema={
                "type": "object",
                "properties": {
                    "hypertable": {
                        "type": "string",
                        "description": "Name of the hypertable"
                    }
                },
                "required": ["hypertable"]
            }
        ),
        Tool(
            name="tsdb_compression_stats",
            description="Show compression statistics for hypertables",
            inputSchema={
                "type": "object",
                "properties": {
                    "hypertable": {
                        "type": "string",
                        "description": "Optional: specific hypertable name"
                    }
                }
            }
        ),
        Tool(
            name="tsdb_add_compression",
            description="Add compression policy to a hypertable",
            inputSchema={
                "type": "object",
                "properties": {
                    "hypertable": {
                        "type": "string",
                        "description": "Name of the hypertable"
                    },
                    "compress_after": {
                        "type": "string",
                        "description": "Compress chunks older than this (e.g., '7 days', '1 month')",
                        "default": "7 days"
                    }
                },
                "required": ["hypertable"]
            }
        ),
        Tool(
            name="tsdb_continuous_aggregate",
            description="Create a continuous aggregate view",
            inputSchema={
                "type": "object",
                "properties": {
                    "view_name": {
                        "type": "string",
                        "description": "Name for the continuous aggregate view"
                    },
                    "query": {
                        "type": "string",
                        "description": "SELECT query with time_bucket"
                    }
                },
                "required": ["view_name", "query"]
            }
        ),
        Tool(
            name="tsdb_time_bucket_query",
            description="Execute a time-bucket aggregation query",
            inputSchema={
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "Table name"
                    },
                    "time_column": {
                        "type": "string",
                        "description": "Time column name",
                        "default": "time"
                    },
                    "bucket_interval": {
                        "type": "string",
                        "description": "Bucket interval (e.g., '5 minutes', '1 hour')",
                        "default": "1 hour"
                    },
                    "aggregates": {
                        "type": "array",
                        "description": "List of aggregations (e.g., ['AVG(temperature)', 'MAX(humidity)'])",
                        "items": {"type": "string"}
                    },
                    "group_by": {
                        "type": "array",
                        "description": "Additional GROUP BY columns",
                        "items": {"type": "string"}
                    },
                    "where": {
                        "type": "string",
                        "description": "Optional WHERE clause"
                    }
                },
                "required": ["table", "aggregates"]
            }
        ),
        Tool(
            name="tsdb_database_stats",
            description="Get database and hypertable statistics",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Execute a tool and return results"""
    try:
        if name == "tsdb_query":
            query = arguments["query"]
            results = await tsdb_server.execute_query(query)
            return [TextContent(
                type="text",
                text=json.dumps(results, indent=2, default=str)
            )]
        
        elif name == "tsdb_execute":
            command = arguments["command"]
            result = await tsdb_server.execute_command(command)
            return [TextContent(
                type="text",
                text=f"Command executed successfully: {result}"
            )]
        
        elif name == "tsdb_create_hypertable":
            table_name = arguments["table_name"]
            time_column = arguments.get("time_column", "time")
            chunk_interval = arguments.get("chunk_time_interval", "1 week")
            
            query = f"""
            SELECT create_hypertable(
                '{table_name}', 
                '{time_column}',
                chunk_time_interval => INTERVAL '{chunk_interval}',
                if_not_exists => TRUE
            );
            """
            result = await tsdb_server.execute_query(query)
            return [TextContent(
                type="text",
                text=f"Hypertable created/verified: {table_name} with {chunk_interval} chunks"
            )]
        
        elif name == "tsdb_show_hypertables":
            query = """
            SELECT 
                hypertable_schema,
                hypertable_name,
                owner,
                num_dimensions,
                num_chunks,
                compression_enabled,
                tablespace
            FROM timescaledb_information.hypertables
            ORDER BY hypertable_schema, hypertable_name;
            """
            results = await tsdb_server.execute_query(query)
            return [TextContent(
                type="text",
                text=json.dumps(results, indent=2, default=str)
            )]
        
        elif name == "tsdb_show_chunks":
            hypertable = arguments["hypertable"]
            query = f"""
            SELECT 
                chunk_name,
                chunk_schema,
                primary_dimension,
                range_start,
                range_end,
                is_compressed,
                pg_size_pretty(total_bytes) as size
            FROM timescaledb_information.chunks
            WHERE hypertable_name = '{hypertable}'
            ORDER BY range_start DESC;
            """
            results = await tsdb_server.execute_query(query)
            return [TextContent(
                type="text",
                text=json.dumps(results, indent=2, default=str)
            )]
        
        elif name == "tsdb_compression_stats":
            hypertable = arguments.get("hypertable")
            where_clause = f"WHERE hypertable_name = '{hypertable}'" if hypertable else ""
            query = f"""
            SELECT 
                hypertable_name,
                chunk_name,
                pg_size_pretty(before_compression_total_bytes) as before_size,
                pg_size_pretty(after_compression_total_bytes) as after_size,
                ROUND(compression_ratio, 2) as compression_ratio
            FROM timescaledb_information.compression_stats
            {where_clause}
            ORDER BY hypertable_name, chunk_name;
            """
            results = await tsdb_server.execute_query(query)
            return [TextContent(
                type="text",
                text=json.dumps(results, indent=2, default=str)
            )]
        
        elif name == "tsdb_add_compression":
            hypertable = arguments["hypertable"]
            compress_after = arguments.get("compress_after", "7 days")
            
            # First enable compression
            enable_query = f"ALTER TABLE {hypertable} SET (timescaledb.compress = true);"
            await tsdb_server.execute_command(enable_query)
            
            # Then add compression policy
            policy_query = f"SELECT add_compression_policy('{hypertable}', INTERVAL '{compress_after}');"
            result = await tsdb_server.execute_query(policy_query)
            
            return [TextContent(
                type="text",
                text=f"Compression enabled for {hypertable}, will compress chunks older than {compress_after}"
            )]
        
        elif name == "tsdb_continuous_aggregate":
            view_name = arguments["view_name"]
            query = arguments["query"]
            
            create_query = f"""
            CREATE MATERIALIZED VIEW {view_name}
            WITH (timescaledb.continuous) AS
            {query}
            """
            await tsdb_server.execute_command(create_query)
            
            return [TextContent(
                type="text",
                text=f"Continuous aggregate '{view_name}' created successfully"
            )]
        
        elif name == "tsdb_time_bucket_query":
            table = arguments["table"]
            time_column = arguments.get("time_column", "time")
            bucket_interval = arguments.get("bucket_interval", "1 hour")
            aggregates = arguments["aggregates"]
            group_by = arguments.get("group_by", [])
            where = arguments.get("where", "")
            
            agg_str = ", ".join(aggregates)
            group_str = ", ".join([str(i+2) for i in range(len(group_by))]) if group_by else ""
            if group_str:
                group_str = ", " + group_str
            group_cols = ", ".join(group_by) if group_by else ""
            if group_cols:
                group_cols = ", " + group_cols
            where_clause = f"WHERE {where}" if where else ""
            
            query = f"""
            SELECT 
                time_bucket('{bucket_interval}', {time_column}) AS bucket
                {group_cols},
                {agg_str}
            FROM {table}
            {where_clause}
            GROUP BY 1{group_str}
            ORDER BY 1 DESC
            LIMIT 100;
            """
            
            results = await tsdb_server.execute_query(query)
            return [TextContent(
                type="text",
                text=json.dumps(results, indent=2, default=str)
            )]
        
        elif name == "tsdb_database_stats":
            query = """
            WITH db_size AS (
                SELECT pg_database_size('timescale') as size
            ),
            hypertable_stats AS (
                SELECT 
                    COUNT(*) as num_hypertables,
                    SUM(num_chunks) as total_chunks,
                    SUM(CASE WHEN compression_enabled THEN 1 ELSE 0 END) as compressed_tables
                FROM timescaledb_information.hypertables
            ),
            continuous_aggs AS (
                SELECT COUNT(*) as num_continuous_aggs
                FROM timescaledb_information.continuous_aggregates
            )
            SELECT 
                pg_size_pretty(db_size.size) as database_size,
                hypertable_stats.num_hypertables,
                hypertable_stats.total_chunks,
                hypertable_stats.compressed_tables,
                continuous_aggs.num_continuous_aggs,
                current_setting('server_version') as postgres_version,
                (SELECT extversion FROM pg_extension WHERE extname = 'timescaledb') as timescaledb_version
            FROM db_size, hypertable_stats, continuous_aggs;
            """
            results = await tsdb_server.execute_query(query)
            return [TextContent(
                type="text",
                text=json.dumps(results[0] if results else {}, indent=2, default=str)
            )]
        
        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
            
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]

@server.list_resources()
async def list_resources() -> List[Resource]:
    """List available resources"""
    return [
        Resource(
            uri="tsdb://hypertables",
            name="Hypertables",
            description="List of all hypertables in TimescaleDB"
        ),
        Resource(
            uri="tsdb://stats",
            name="Database Statistics",
            description="TimescaleDB database statistics and metrics"
        )
    ]

@server.read_resource()
async def read_resource(uri: str) -> str:
    """Get resource content"""
    if uri == "tsdb://hypertables":
        query = """
        SELECT 
            hypertable_schema,
            hypertable_name,
            owner,
            num_dimensions,
            num_chunks,
            compression_enabled
        FROM timescaledb_information.hypertables
        ORDER BY hypertable_schema, hypertable_name;
        """
        results = await tsdb_server.execute_query(query)
        return json.dumps(results, indent=2, default=str)
    
    elif uri == "tsdb://stats":
        query = """
        SELECT 
            pg_size_pretty(pg_database_size('timescale')) as database_size,
            (SELECT COUNT(*) FROM timescaledb_information.hypertables) as hypertables,
            (SELECT SUM(num_chunks) FROM timescaledb_information.hypertables) as total_chunks,
            (SELECT extversion FROM pg_extension WHERE extname = 'timescaledb') as version
        """
        results = await tsdb_server.execute_query(query)
        return json.dumps(results[0] if results else {}, indent=2, default=str)
    
    else:
        return f"Unknown resource: {uri}"

async def main():
    """Main entry point"""
    # Initialize database connection
    await tsdb_server.initialize()
    
    try:
        # Import required types
        from mcp.server import InitializationOptions
        from mcp.types import ServerCapabilities
        
        # Create initialization options
        init_options = InitializationOptions(
            server_name="mcp-timescaledb",
            server_version="1.0.0",
            capabilities=ServerCapabilities(
                tools={},  # Tools are handled by decorators
                resources={} # Resources are handled by decorators
            )
        )
        
        # Run the MCP server
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, 
                write_stream,
                initialization_options=init_options
            )
    finally:
        # Cleanup
        await tsdb_server.cleanup()

if __name__ == "__main__":
    asyncio.run(main())