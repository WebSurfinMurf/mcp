#!/usr/bin/env python3
"""
TimescaleDB HTTP-Native MCP Service
Provides time-series database operations via HTTP REST API
"""

import os
import json
import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration from environment
DB_CONFIG = {
    "host": os.getenv("TSDB_HOST", "timescaledb"),
    "port": int(os.getenv("TSDB_PORT", "5432")),  # Internal port, not external 5433
    "database": os.getenv("TSDB_DATABASE", "timescale"),
    "user": os.getenv("TSDB_USER", "tsdbadmin"),
    "password": os.getenv("TSDB_PASSWORD"),
    "min_size": 2,
    "max_size": 10,
    "command_timeout": 60,
    "server_settings": {
        "application_name": "mcp-timescaledb-http"
    }
}

# Global database pool
db_pool: Optional[asyncpg.Pool] = None

# Request/Response Models
class ToolRequest(BaseModel):
    input: Dict[str, Any] = Field(default_factory=dict)

class ToolResponse(BaseModel):
    tool: str
    result: Union[str, Dict[str, Any]]
    requestId: int
    timestamp: str
    status: str

class HealthResponse(BaseModel):
    status: str
    service: str
    database: str
    timestamp: str
    pool_stats: Optional[Dict[str, Any]] = None

class ServiceInfo(BaseModel):
    name: str
    version: str
    description: str
    tools_count: int
    database_connection: str
    timestamp: str

# Database Connection Management
class TimescaleDBManager:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Initialize database connection pool - SINGLE LOG MESSAGE"""
        try:
            self.pool = await asyncpg.create_pool(**DB_CONFIG)
            # Test connection with a simple query
            async with self.pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info(f"TimescaleDB HTTP service initialized successfully - {version[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize TimescaleDB connection: {e}")
            return False

    async def cleanup(self):
        """Clean up database connections"""
        if self.pool:
            await self.pool.close()
            logger.info("TimescaleDB connection pool closed")

    async def execute_query(self, query: str, params: List[Any] = None) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results as list of dicts"""
        if not self.pool:
            raise HTTPException(status_code=503, detail="Database not connected")

        try:
            async with self.pool.acquire() as conn:
                if params:
                    rows = await conn.fetch(query, *params)
                else:
                    rows = await conn.fetch(query)

                # Convert rows to list of dicts
                result = []
                for row in rows:
                    result.append(dict(row))
                return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

    async def execute_command(self, command: str, params: List[Any] = None) -> str:
        """Execute non-SELECT command and return status"""
        if not self.pool:
            raise HTTPException(status_code=503, detail="Database not connected")

        try:
            async with self.pool.acquire() as conn:
                if params:
                    result = await conn.execute(command, *params)
                else:
                    result = await conn.execute(command)
                return result
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise HTTPException(status_code=500, detail=f"Command failed: {str(e)}")

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        if not self.pool:
            return {"status": "not_connected"}

        return {
            "size": self.pool.get_size(),
            "idle": self.pool.get_idle_size(),
            "max_size": self.pool.get_max_size(),
            "min_size": self.pool.get_min_size()
        }

# Global database manager
db_manager = TimescaleDBManager()

# FastAPI Application Lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting TimescaleDB HTTP service...")
    success = await db_manager.initialize()
    if not success:
        logger.error("Failed to initialize database - service may not work correctly")

    yield

    # Shutdown
    logger.info("Shutting down TimescaleDB HTTP service...")
    await db_manager.cleanup()

# FastAPI Application
app = FastAPI(
    title="TimescaleDB HTTP MCP Service",
    description="HTTP-native TimescaleDB MCP service providing time-series database operations",
    version="1.0.0",
    lifespan=lifespan
)

# Utility Functions
def generate_request_id() -> int:
    """Generate unique request ID"""
    return int(time.time() * 1000)

def get_timestamp() -> str:
    """Get current ISO timestamp"""
    return datetime.now().isoformat() + "Z"

def create_response(tool_name: str, result: Union[str, Dict[str, Any]], request_id: int = None) -> ToolResponse:
    """Create standardized tool response"""
    return ToolResponse(
        tool=tool_name,
        result=result,
        requestId=request_id or generate_request_id(),
        timestamp=get_timestamp(),
        status="success"
    )

# Core Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    database_status = "connected" if db_manager.pool else "disconnected"
    pool_stats = db_manager.get_pool_stats()

    return HealthResponse(
        status="ok",
        service="timescaledb-http-service",
        database=database_status,
        timestamp=get_timestamp(),
        pool_stats=pool_stats
    )

@app.get("/info", response_model=ServiceInfo)
async def service_info():
    """Service information endpoint"""
    return ServiceInfo(
        name="TimescaleDB HTTP MCP Service",
        version="1.0.0",
        description="HTTP-native service providing TimescaleDB time-series database operations",
        tools_count=9,
        database_connection=f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}",
        timestamp=get_timestamp()
    )

@app.get("/tools")
async def list_tools():
    """List all available tools"""
    tools = [
        {
            "name": "tsdb_query",
            "description": "Execute SELECT queries against TimescaleDB",
            "parameters": ["query", "params"]
        },
        {
            "name": "tsdb_execute",
            "description": "Execute non-SELECT SQL commands",
            "parameters": ["command", "params"]
        },
        {
            "name": "tsdb_create_hypertable",
            "description": "Convert regular table to TimescaleDB hypertable",
            "parameters": ["table_name", "time_column", "chunk_time_interval"]
        },
        {
            "name": "tsdb_show_hypertables",
            "description": "List all hypertables with metadata",
            "parameters": []
        },
        {
            "name": "tsdb_show_chunks",
            "description": "Show chunks for specified hypertable",
            "parameters": ["hypertable"]
        },
        {
            "name": "tsdb_compression_stats",
            "description": "View compression statistics for hypertables",
            "parameters": ["hypertable"]
        },
        {
            "name": "tsdb_add_compression",
            "description": "Add compression policy to hypertable",
            "parameters": ["hypertable", "compress_after"]
        },
        {
            "name": "tsdb_continuous_aggregate",
            "description": "Create continuous aggregate view",
            "parameters": ["view_name", "query"]
        },
        {
            "name": "tsdb_database_stats",
            "description": "Get comprehensive database statistics",
            "parameters": []
        }
    ]

    return {
        "service": "timescaledb-http-service",
        "tools": tools,
        "total_tools": len(tools),
        "timestamp": get_timestamp()
    }

# Tool Implementation Endpoints
@app.post("/tools/tsdb_query", response_model=ToolResponse)
async def tsdb_query(request: ToolRequest):
    """Execute SELECT queries against TimescaleDB"""
    request_id = generate_request_id()

    try:
        query = request.input.get("query")
        params = request.input.get("params", [])

        if not query:
            raise HTTPException(status_code=400, detail="Query parameter is required")

        if not query.strip().upper().startswith("SELECT"):
            raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")

        start_time = time.time()
        rows = await db_manager.execute_query(query, params)
        execution_time = (time.time() - start_time) * 1000

        result = {
            "success": True,
            "rows": rows,
            "row_count": len(rows),
            "execution_time_ms": round(execution_time, 2),
            "query": query[:100] + "..." if len(query) > 100 else query
        }

        return create_response("tsdb_query", result, request_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"tsdb_query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")

@app.post("/tools/tsdb_execute", response_model=ToolResponse)
async def tsdb_execute(request: ToolRequest):
    """Execute non-SELECT SQL commands"""
    request_id = generate_request_id()

    try:
        command = request.input.get("command")
        params = request.input.get("params", [])

        if not command:
            raise HTTPException(status_code=400, detail="Command parameter is required")

        # Block dangerous commands
        dangerous_keywords = ["DROP DATABASE", "DROP USER", "DELETE FROM pg_", "TRUNCATE pg_"]
        command_upper = command.upper()
        for keyword in dangerous_keywords:
            if keyword in command_upper:
                raise HTTPException(status_code=403, detail=f"Command contains forbidden keyword: {keyword}")

        start_time = time.time()
        result_status = await db_manager.execute_command(command, params)
        execution_time = (time.time() - start_time) * 1000

        result = {
            "success": True,
            "status": result_status,
            "execution_time_ms": round(execution_time, 2),
            "command": command[:100] + "..." if len(command) > 100 else command
        }

        return create_response("tsdb_execute", result, request_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"tsdb_execute failed: {e}")
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}")

@app.post("/tools/tsdb_show_hypertables", response_model=ToolResponse)
async def tsdb_show_hypertables(request: ToolRequest):
    """List all hypertables with metadata"""
    request_id = generate_request_id()

    try:
        query = """
        SELECT
            hypertable_schema,
            hypertable_name,
            owner,
            num_dimensions,
            num_chunks,
            compression_enabled,
            tablespaces,
            primary_dimension,
            primary_dimension_type
        FROM timescaledb_information.hypertables
        ORDER BY hypertable_schema, hypertable_name;
        """

        rows = await db_manager.execute_query(query)

        result = {
            "success": True,
            "hypertables": rows,
            "total_count": len(rows)
        }

        return create_response("tsdb_show_hypertables", result, request_id)

    except Exception as e:
        logger.error(f"tsdb_show_hypertables failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list hypertables: {str(e)}")

@app.post("/tools/tsdb_create_hypertable", response_model=ToolResponse)
async def tsdb_create_hypertable(request: ToolRequest):
    """Convert regular table to TimescaleDB hypertable"""
    request_id = generate_request_id()

    try:
        table_name = request.input.get("table_name")
        time_column = request.input.get("time_column", "time")
        chunk_time_interval = request.input.get("chunk_time_interval", "1 week")

        if not table_name:
            raise HTTPException(status_code=400, detail="table_name parameter is required")

        # Create hypertable
        command = f"SELECT create_hypertable('{table_name}', '{time_column}', chunk_time_interval => interval '{chunk_time_interval}');"

        await db_manager.execute_command(command)

        result = {
            "success": True,
            "message": f"Successfully created hypertable {table_name}",
            "table_name": table_name,
            "time_column": time_column,
            "chunk_time_interval": chunk_time_interval
        }

        return create_response("tsdb_create_hypertable", result, request_id)

    except Exception as e:
        logger.error(f"tsdb_create_hypertable failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create hypertable: {str(e)}")

@app.post("/tools/tsdb_show_chunks", response_model=ToolResponse)
async def tsdb_show_chunks(request: ToolRequest):
    """Show chunks for specified hypertable"""
    request_id = generate_request_id()

    try:
        hypertable = request.input.get("hypertable")

        if not hypertable:
            raise HTTPException(status_code=400, detail="hypertable parameter is required")

        query = """
        SELECT
            chunk_schema,
            chunk_name,
            hypertable_name,
            primary_dimension,
            primary_dimension_type,
            range_start,
            range_end,
            range_start_integer,
            range_end_integer,
            is_compressed,
            chunk_creation_time
        FROM timescaledb_information.chunks
        WHERE hypertable_name = $1
        ORDER BY range_start;
        """

        rows = await db_manager.execute_query(query, [hypertable])

        result = {
            "success": True,
            "hypertable": hypertable,
            "chunks": rows,
            "total_chunks": len(rows)
        }

        return create_response("tsdb_show_chunks", result, request_id)

    except Exception as e:
        logger.error(f"tsdb_show_chunks failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to show chunks: {str(e)}")

@app.post("/tools/tsdb_compression_stats", response_model=ToolResponse)
async def tsdb_compression_stats(request: ToolRequest):
    """View compression statistics for hypertables"""
    request_id = generate_request_id()

    try:
        hypertable = request.input.get("hypertable")

        if hypertable:
            # Stats for specific hypertable
            query = """
            SELECT
                hypertable_name,
                before_compression_table_bytes,
                before_compression_index_bytes,
                before_compression_toast_bytes,
                before_compression_total_bytes,
                after_compression_table_bytes,
                after_compression_index_bytes,
                after_compression_toast_bytes,
                after_compression_total_bytes,
                compression_ratio
            FROM timescaledb_information.compressed_hypertable_stats
            WHERE hypertable_name = $1;
            """
            rows = await db_manager.execute_query(query, [hypertable])
        else:
            # Stats for all hypertables
            query = """
            SELECT
                hypertable_name,
                before_compression_table_bytes,
                before_compression_index_bytes,
                before_compression_toast_bytes,
                before_compression_total_bytes,
                after_compression_table_bytes,
                after_compression_index_bytes,
                after_compression_toast_bytes,
                after_compression_total_bytes,
                compression_ratio
            FROM timescaledb_information.compressed_hypertable_stats
            ORDER BY hypertable_name;
            """
            rows = await db_manager.execute_query(query)

        result = {
            "success": True,
            "compression_stats": rows,
            "total_hypertables": len(rows),
            "filter": hypertable if hypertable else "all"
        }

        return create_response("tsdb_compression_stats", result, request_id)

    except Exception as e:
        logger.error(f"tsdb_compression_stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get compression stats: {str(e)}")

@app.post("/tools/tsdb_add_compression", response_model=ToolResponse)
async def tsdb_add_compression(request: ToolRequest):
    """Add compression policy to hypertable"""
    request_id = generate_request_id()

    try:
        hypertable = request.input.get("hypertable")
        compress_after = request.input.get("compress_after", "7 days")

        if not hypertable:
            raise HTTPException(status_code=400, detail="hypertable parameter is required")

        # Add compression policy
        command = f"SELECT add_compression_policy('{hypertable}', compress_after => interval '{compress_after}');"

        await db_manager.execute_command(command)

        result = {
            "success": True,
            "message": f"Successfully added compression policy to {hypertable}",
            "hypertable": hypertable,
            "compress_after": compress_after
        }

        return create_response("tsdb_add_compression", result, request_id)

    except Exception as e:
        logger.error(f"tsdb_add_compression failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add compression policy: {str(e)}")

@app.post("/tools/tsdb_continuous_aggregate", response_model=ToolResponse)
async def tsdb_continuous_aggregate(request: ToolRequest):
    """Create continuous aggregate view"""
    request_id = generate_request_id()

    try:
        view_name = request.input.get("view_name")
        query = request.input.get("query")

        if not view_name or not query:
            raise HTTPException(status_code=400, detail="view_name and query parameters are required")

        # Create continuous aggregate
        command = f"""
        CREATE MATERIALIZED VIEW {view_name}
        WITH (timescaledb.continuous) AS
        {query};
        """

        await db_manager.execute_command(command)

        result = {
            "success": True,
            "message": f"Successfully created continuous aggregate view {view_name}",
            "view_name": view_name,
            "query": query
        }

        return create_response("tsdb_continuous_aggregate", result, request_id)

    except Exception as e:
        logger.error(f"tsdb_continuous_aggregate failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create continuous aggregate: {str(e)}")

@app.post("/tools/tsdb_database_stats", response_model=ToolResponse)
async def tsdb_database_stats(request: ToolRequest):
    """Get comprehensive database statistics"""
    request_id = generate_request_id()

    try:
        # Get database size
        db_size_query = "SELECT pg_size_pretty(pg_database_size(current_database())) as database_size;"
        db_size = await db_manager.execute_query(db_size_query)

        # Get table count
        table_count_query = "SELECT count(*) as table_count FROM information_schema.tables WHERE table_schema = 'public';"
        table_count = await db_manager.execute_query(table_count_query)

        # Get hypertable count
        hypertable_count_query = "SELECT count(*) as hypertable_count FROM timescaledb_information.hypertables;"
        hypertable_count = await db_manager.execute_query(hypertable_count_query)

        # Get version
        version_query = "SELECT version() as version;"
        version = await db_manager.execute_query(version_query)

        # Get TimescaleDB version
        tsdb_version_query = "SELECT extversion as timescaledb_version FROM pg_extension WHERE extname = 'timescaledb';"
        tsdb_version = await db_manager.execute_query(tsdb_version_query)

        result = {
            "success": True,
            "database_size": db_size[0]["database_size"] if db_size else "unknown",
            "table_count": table_count[0]["table_count"] if table_count else 0,
            "hypertable_count": hypertable_count[0]["hypertable_count"] if hypertable_count else 0,
            "postgresql_version": version[0]["version"][:50] + "..." if version else "unknown",
            "timescaledb_version": tsdb_version[0]["timescaledb_version"] if tsdb_version else "unknown",
            "connection_pool": db_manager.get_pool_stats()
        }

        return create_response("tsdb_database_stats", result, request_id)

    except Exception as e:
        logger.error(f"tsdb_database_stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get database stats: {str(e)}")

# Error Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "tool": "error",
            "result": {"error": exc.detail, "status_code": exc.status_code},
            "requestId": generate_request_id(),
            "timestamp": get_timestamp(),
            "status": "error"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "tool": "error",
            "result": {"error": "Internal server error", "details": str(exc)},
            "requestId": generate_request_id(),
            "timestamp": get_timestamp(),
            "status": "error"
        }
    )

# Main entry point
if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        access_log=True
    )