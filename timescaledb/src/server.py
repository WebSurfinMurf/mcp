"""
MCP TimescaleDB Server
Provides PostgreSQL/TimescaleDB database tools via MCP endpoint
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

app = FastAPI(title="MCP TimescaleDB Server", version="1.0.0")

# Configuration
MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "timescaledb")
DATABASE_URI = os.getenv("DATABASE_URI", "postgresql://tsdbadmin:TimescaleSecure2025@timescaledb:5432/timescale")

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

class TimescaleDBTools:
    """MCP tool implementations for TimescaleDB operations"""

    @staticmethod
    async def execute_query(query: str, params: List = None) -> Dict[str, Any]:
        """Execute a SQL query against TimescaleDB"""
        try:
            async with db_pool.acquire() as conn:
                # For security, only allow SELECT queries and basic SHOW commands
                query_upper = query.strip().upper()
                if not (query_upper.startswith('SELECT') or
                       query_upper.startswith('SHOW') or
                       query_upper.startswith('\\L') or
                       query_upper.startswith('\\D') or
                       'INFORMATION_SCHEMA' in query_upper):
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
            query = "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname"
            return await TimescaleDBTools.execute_query(query)
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def list_tables(schema: str = "public") -> Dict[str, Any]:
        """List all tables in a schema"""
        try:
            query = """
                SELECT table_name, table_type
                FROM information_schema.tables
                WHERE table_schema = $1
                ORDER BY table_name
            """
            return await TimescaleDBTools.execute_query(query, [schema])
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
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = $1 AND table_name = $2
                ORDER BY ordinal_position
            """
            return await TimescaleDBTools.execute_query(query, [schema, table_name])
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def get_table_stats(table_name: str, schema: str = "public") -> Dict[str, Any]:
        """Get statistics about a table"""
        try:
            query = f"""
                SELECT
                    COUNT(*) as row_count,
                    pg_size_pretty(pg_total_relation_size('{schema}.{table_name}')) as total_size
            """
            return await TimescaleDBTools.execute_query(query)
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def list_hypertables() -> Dict[str, Any]:
        """List TimescaleDB hypertables"""
        try:
            query = """
                SELECT
                    hypertable_schema,
                    hypertable_name,
                    owner,
                    num_dimensions,
                    num_chunks,
                    table_bytes,
                    index_bytes,
                    toast_bytes,
                    total_bytes
                FROM timescaledb_information.hypertables
                ORDER BY hypertable_schema, hypertable_name
            """
            return await TimescaleDBTools.execute_query(query)
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
                    "name": f"TimescaleDB-MCP ({MCP_SERVER_NAME})",
                    "version": "1.0.0"
                }
            },
            id=request.id
        )

    elif request.method == "tools/list":
        tools = [
            {
                "name": "execute_query",
                "description": "Execute a SELECT query against TimescaleDB",
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
                "description": "List all databases in the TimescaleDB instance",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "list_tables",
                "description": "List all tables in a schema",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "schema": {"type": "string", "description": "Schema name", "default": "public"}
                    }
                }
            },
            {
                "name": "describe_table",
                "description": "Describe the structure of a table",
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
                "description": "Get statistics about a table",
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
                "name": "list_hypertables",
                "description": "List TimescaleDB hypertables",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

        return MCPResponse(result={"tools": tools}, id=request.id)

    elif request.method == "tools/call":
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})

        if tool_name == "execute_query":
            result = await TimescaleDBTools.execute_query(**arguments)
        elif tool_name == "list_databases":
            result = await TimescaleDBTools.list_databases()
        elif tool_name == "list_tables":
            result = await TimescaleDBTools.list_tables(**arguments)
        elif tool_name == "describe_table":
            result = await TimescaleDBTools.describe_table(**arguments)
        elif tool_name == "get_table_stats":
            result = await TimescaleDBTools.get_table_stats(**arguments)
        elif tool_name == "list_hypertables":
            result = await TimescaleDBTools.list_hypertables()
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

@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for MCP communication"""

    async def event_stream():
        """Generate SSE events"""
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connection', 'server': MCP_SERVER_NAME})}\\n\\n"

        try:
            while True:
                # Handle MCP requests from client
                if await request.is_disconnected():
                    break

                # For now, just send periodic ping
                await asyncio.sleep(30)
                yield f"data: {json.dumps({'type': 'ping', 'timestamp': asyncio.get_event_loop().time()})}\\n\\n"

        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }
    )

@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """HTTP POST endpoint for MCP requests"""
    response = await handle_mcp_request(request)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)