"""
MCP PostgreSQL Server
Provides enhanced PostgreSQL database tools via MCP endpoint
"""
import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Union
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncpg
import logging

app = FastAPI(title="MCP PostgreSQL Server", version="1.0.0")

# Configuration
MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "postgres")
DATABASE_URI = os.getenv("DATABASE_URI", "postgresql://admin:Pass123qp@postgres:5432/postgres")

# Database connection pool
db_pool = None

class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

class PostgreSQLTools:
    """MCP tool implementations for PostgreSQL operations"""

    @staticmethod
    async def execute_query(query: str, params: List = None) -> Dict[str, Any]:
        """Execute a SQL query against PostgreSQL"""
        try:
            async with db_pool.acquire() as conn:
                # For security, only allow SELECT queries and basic SHOW commands
                query_upper = query.strip().upper()
                if not (query_upper.startswith('SELECT') or
                       query_upper.startswith('SHOW') or
                       query_upper.startswith('\\L') or
                       query_upper.startswith('\\D') or
                       'INFORMATION_SCHEMA' in query_upper or
                       query_upper.startswith('WITH')):  # Allow CTEs
                    return {
                        "error": "Only SELECT, SHOW, and schema queries allowed for security",
                        "success": False
                    }

                result = await conn.fetch(query, *(params or []))

                # Convert result to list of dictionaries
                rows = []
                for row in result:
                    rows.append(dict(row))

                return {
                    "query": query,
                    "rows": rows,
                    "row_count": len(rows),
                    "success": True
                }
        except Exception as e:
            return {
                "error": str(e),
                "query": query,
                "success": False
            }

    @staticmethod
    async def list_databases() -> Dict[str, Any]:
        """List all databases"""
        try:
            query = """
                SELECT
                    datname as database_name,
                    pg_size_pretty(pg_database_size(datname)) as size,
                    pg_encoding_to_char(encoding) as encoding,
                    datcollate as collation
                FROM pg_database
                WHERE datistemplate = false
                ORDER BY datname
            """
            return await PostgreSQLTools.execute_query(query)
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def list_schemas(database: str = None) -> Dict[str, Any]:
        """List all schemas in the current database"""
        try:
            query = """
                SELECT
                    schema_name,
                    schema_owner
                FROM information_schema.schemata
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                ORDER BY schema_name
            """
            return await PostgreSQLTools.execute_query(query)
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def list_tables(schema: str = "public") -> Dict[str, Any]:
        """List all tables in a schema"""
        try:
            query = """
                SELECT
                    table_name,
                    table_type,
                    pg_size_pretty(pg_total_relation_size(quote_ident(table_schema) || '.' || quote_ident(table_name))) as size
                FROM information_schema.tables
                WHERE table_schema = $1
                ORDER BY table_name
            """
            return await PostgreSQLTools.execute_query(query, [schema])
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def describe_table(table_name: str, schema: str = "public") -> Dict[str, Any]:
        """Describe the structure of a table"""
        try:
            query = """
                SELECT
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default,
                    ordinal_position
                FROM information_schema.columns
                WHERE table_schema = $1 AND table_name = $2
                ORDER BY ordinal_position
            """
            return await PostgreSQLTools.execute_query(query, [schema, table_name])
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def get_table_stats(table_name: str, schema: str = "public") -> Dict[str, Any]:
        """Get statistics about a table"""
        try:
            query = f"""
                SELECT
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) as total_size,
                    pg_size_pretty(pg_relation_size(schemaname || '.' || tablename)) as table_size,
                    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename) - pg_relation_size(schemaname || '.' || tablename)) as indexes_size,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables
                WHERE schemaname = $1 AND tablename = $2
            """
            return await PostgreSQLTools.execute_query(query, [schema, table_name])
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def list_indexes(table_name: str = None, schema: str = "public") -> Dict[str, Any]:
        """List indexes in a schema or for a specific table"""
        try:
            if table_name:
                query = """
                    SELECT
                        indexname as index_name,
                        tablename as table_name,
                        indexdef as definition
                    FROM pg_indexes
                    WHERE schemaname = $1 AND tablename = $2
                    ORDER BY indexname
                """
                return await PostgreSQLTools.execute_query(query, [schema, table_name])
            else:
                query = """
                    SELECT
                        indexname as index_name,
                        tablename as table_name,
                        indexdef as definition
                    FROM pg_indexes
                    WHERE schemaname = $1
                    ORDER BY tablename, indexname
                """
                return await PostgreSQLTools.execute_query(query, [schema])
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def get_table_constraints(table_name: str, schema: str = "public") -> Dict[str, Any]:
        """Get all constraints for a table"""
        try:
            query = """
                SELECT
                    tc.constraint_name,
                    tc.constraint_type,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                LEFT JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                LEFT JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.table_schema = $1 AND tc.table_name = $2
                ORDER BY tc.constraint_type, tc.constraint_name
            """
            return await PostgreSQLTools.execute_query(query, [schema, table_name])
        except Exception as e:
            return {"error": str(e), "success": False}

async def init_db_pool():
    """Initialize database connection pool"""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URI, min_size=1, max_size=5)
        logging.info("Database connection pool initialized")
    except Exception as e:
        logging.error(f"Failed to initialize database pool: {e}")
        raise

async def handle_mcp_request(request: MCPRequest) -> MCPResponse:
    """Handle MCP method calls"""

    if request.method == "initialize":
        return MCPResponse(
            result={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "prompts": {},
                    "resources": {}
                },
                "serverInfo": {
                    "name": f"PostgreSQL-MCP ({MCP_SERVER_NAME})",
                    "version": "1.0.0"
                }
            },
            id=request.id
        )

    elif request.method == "tools/list":
        tools = [
            {
                "name": "execute_query",
                "description": "Execute a SELECT query against PostgreSQL database",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SQL SELECT query to execute"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "list_databases",
                "description": "List all databases with size and encoding information",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "list_schemas",
                "description": "List all schemas in the current database",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "list_tables",
                "description": "List all tables in a schema with size information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "schema": {"type": "string", "description": "Schema name", "default": "public"}
                    }
                }
            },
            {
                "name": "describe_table",
                "description": "Describe the structure of a table including columns and types",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "Name of the table to describe"},
                        "schema": {"type": "string", "description": "Schema name", "default": "public"}
                    },
                    "required": ["table_name"]
                }
            },
            {
                "name": "get_table_stats",
                "description": "Get statistics about a table including size, row counts, and vacuum info",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "Name of the table"},
                        "schema": {"type": "string", "description": "Schema name", "default": "public"}
                    },
                    "required": ["table_name"]
                }
            },
            {
                "name": "list_indexes",
                "description": "List indexes in a schema or for a specific table",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "Optional: specific table name"},
                        "schema": {"type": "string", "description": "Schema name", "default": "public"}
                    }
                }
            },
            {
                "name": "get_table_constraints",
                "description": "Get all constraints (primary key, foreign key, unique, check) for a table",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "Name of the table"},
                        "schema": {"type": "string", "description": "Schema name", "default": "public"}
                    },
                    "required": ["table_name"]
                }
            }
        ]

        return MCPResponse(result={"tools": tools}, id=request.id)

    elif request.method == "tools/call":
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})

        if tool_name == "execute_query":
            result = await PostgreSQLTools.execute_query(**arguments)
        elif tool_name == "list_databases":
            result = await PostgreSQLTools.list_databases()
        elif tool_name == "list_schemas":
            result = await PostgreSQLTools.list_schemas(**arguments)
        elif tool_name == "list_tables":
            result = await PostgreSQLTools.list_tables(**arguments)
        elif tool_name == "describe_table":
            result = await PostgreSQLTools.describe_table(**arguments)
        elif tool_name == "get_table_stats":
            result = await PostgreSQLTools.get_table_stats(**arguments)
        elif tool_name == "list_indexes":
            result = await PostgreSQLTools.list_indexes(**arguments)
        elif tool_name == "get_table_constraints":
            result = await PostgreSQLTools.get_table_constraints(**arguments)
        else:
            return MCPResponse(
                error={"code": -32601, "message": f"Unknown tool: {tool_name}"},
                id=request.id
            )

        return MCPResponse(result={"content": [{"type": "text", "text": json.dumps(result)}]}, id=request.id)

    else:
        return MCPResponse(
            error={"code": -32601, "message": f"Unknown method: {request.method}"},
            id=request.id
        )

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    await init_db_pool()

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown"""
    global db_pool
    if db_pool:
        await db_pool.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": MCP_SERVER_NAME,
        "database": "connected" if db_pool else "disconnected"
    }

@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """HTTP POST endpoint for MCP requests"""
    response = await handle_mcp_request(request)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
