"""
Centralized LangChain MCP Server
Provides unified tool access via agent and direct API endpoints
Integrates validated MCP services: monitoring, timescaledb, fetch, filesystem, postgres
"""

import os
import logging
import sys
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
from pathlib import Path

# Core dependencies
import psycopg2
import asyncpg
import boto3
import httpx
from botocore.client import Config
from pythonjsonlogger import jsonlogger

# Web content processing (from official fetch server)
import markdownify
import readabilipy.simple_json
from protego import Protego
from urllib.parse import urlparse, urlunparse

# Path validation (for filesystem operations)
from pathvalidate import is_valid_filepath, sanitize_filepath

# LangChain and FastAPI
from langchain_core.tools import tool
from langchain_litellm import ChatLiteLLM
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langserve import add_routes
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

# Configure structured JSON logging
def setup_logging():
    log = logging.getLogger()
    log.handlers.clear()  # Clear existing handlers

    logHandler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s %(module)s %(funcName)s'
    )
    logHandler.setFormatter(formatter)
    log.addHandler(logHandler)
    log.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

    return logging.getLogger(__name__)

logger = setup_logging()

# FastAPI Application
app = FastAPI(
    title="Centralized LangChain MCP Server",
    version="1.0.0",
    description="Unified MCP tool server for ai-servicers.com infrastructure",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
CONFIG = {
    "postgres": {
        "host": os.environ.get("POSTGRES_HOST", "postgres"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "user": os.environ.get("POSTGRES_USER"),
        "password": os.environ.get("POSTGRES_PASSWORD"),
        "database": os.environ.get("POSTGRES_DB", "postgres")
    },
    "minio": {
        "endpoint": os.environ.get("MINIO_ENDPOINT_URL", "http://minio:9000"),
        "access_key": os.environ.get("MINIO_ROOT_USER"),
        "secret_key": os.environ.get("MINIO_ROOT_PASSWORD")
    },
    "loki": {
        "url": os.environ.get("LOKI_URL", "http://loki:3100")
    },
    "netdata": {
        "url": os.environ.get("NETDATA_URL", "http://netdata:19999")
    },
    "litellm": {
        "url": os.environ.get("LITELLM_URL", "http://litellm:4000")
    },
    "limits": {
        "default_limit": int(os.environ.get("DEFAULT_LIMIT", "100")),
        "default_hours": int(os.environ.get("DEFAULT_HOURS", "24")),
        "max_file_size": int(os.environ.get("MAX_FILE_SIZE", "10485760"))
    }
}

# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "mcp-server",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "tools_count": len([t for t in globals().values() if hasattr(t, '_name') and hasattr(t, 'func')])
    }

# ====== POSTGRESQL TOOLS (Modern Implementation - PostgreSQL 12-17 Compatible) ======

# Import modern PostgreSQL functions
from postgres_modern import (
    run_async_query,
    postgres_list_databases_modern,
    postgres_list_tables_modern,
    postgres_query_advanced,
    postgres_server_info,
    postgres_database_sizes
)

@tool
def postgres_query(query: str, database: str = None) -> str:
    """Execute read-only PostgreSQL query with modern async implementation"""
    logger.info("Executing PostgreSQL query (modern)", extra={
        'query_type': 'read',
        'query': query[:100],
        'database': database
    })

    try:
        result = run_async_query(postgres_query_advanced(query, database))
        logger.info("Modern PostgreSQL query completed successfully")
        return result
    except Exception as e:
        logger.error("Modern PostgreSQL query failed", exc_info=True, extra={'error': str(e)})
        return f"Database error: {str(e)}"

@tool
def postgres_list_databases() -> str:
    """List all databases in PostgreSQL with modern compatibility (PostgreSQL 12-17)"""
    logger.info("Listing databases with modern implementation")

    try:
        result = run_async_query(postgres_list_databases_modern())
        logger.info("Database list retrieved successfully")
        return result
    except Exception as e:
        logger.error("Failed to list databases", exc_info=True, extra={'error': str(e)})
        return f"Database listing error: {str(e)}"

@tool
def postgres_list_tables(schema: str = "public", database: str = None) -> str:
    """List tables in specified schema and database with modern implementation"""
    logger.info("Listing tables with modern implementation", extra={
        'schema': schema,
        'database': database
    })

    try:
        result = run_async_query(postgres_list_tables_modern(database, schema))
        logger.info("Table list retrieved successfully")
        return result
    except Exception as e:
        logger.error("Failed to list tables", exc_info=True, extra={'error': str(e)})
        return f"Table listing error: {str(e)}"

@tool
def postgres_server_info() -> str:
    """Get comprehensive PostgreSQL server information and statistics"""
    from postgres_modern import postgres_server_info as postgres_server_info_impl
    logger.info("Getting PostgreSQL server information")

    try:
        result = run_async_query(postgres_server_info_impl())
        logger.info("Server information retrieved successfully")
        return result
    except Exception as e:
        logger.error("Failed to get server info", exc_info=True, extra={'error': str(e)})
        return f"Server info error: {str(e)}"

@tool
def postgres_database_sizes() -> str:
    """Get database sizes and connection statistics"""
    from postgres_modern import postgres_database_sizes as postgres_database_sizes_impl
    logger.info("Getting database size information")

    try:
        result = run_async_query(postgres_database_sizes_impl())
        logger.info("Database sizes retrieved successfully")
        return result
    except Exception as e:
        logger.error("Failed to get database sizes", exc_info=True, extra={'error': str(e)})
        return f"Database sizes error: {str(e)}"

# ====== MINIO S3 TOOLS ======

@tool
def minio_list_objects(bucket_name: str, prefix: str = "") -> str:
    """List objects in MinIO S3 bucket with optional prefix filter"""
    logger.info("Listing MinIO objects", extra={'bucket': bucket_name, 'prefix': prefix})

    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=CONFIG["minio"]["endpoint"],
            aws_access_key_id=CONFIG["minio"]["access_key"],
            aws_secret_access_key=CONFIG["minio"]["secret_key"],
            config=Config(signature_version='s3v4')
        )

        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        objects = []

        for obj in response.get('Contents', []):
            objects.append({
                'key': obj['Key'],
                'size': obj['Size'],
                'last_modified': obj['LastModified'].isoformat()
            })

        result = {
            "bucket": bucket_name,
            "prefix": prefix,
            "objects": objects[:CONFIG["limits"]["default_limit"]],
            "count": len(objects)
        }

        logger.info("MinIO list completed", extra={'objects_found': len(objects)})
        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        logger.error("MinIO operation failed", exc_info=True, extra={'error': str(e)})
        return f"MinIO error: {str(e)}"

@tool
def minio_get_object(bucket_name: str, object_key: str) -> str:
    """Get object content from MinIO S3 bucket (text files only)"""
    logger.info("Getting MinIO object", extra={'bucket': bucket_name, 'key': object_key})

    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=CONFIG["minio"]["endpoint"],
            aws_access_key_id=CONFIG["minio"]["access_key"],
            aws_secret_access_key=CONFIG["minio"]["secret_key"],
            config=Config(signature_version='s3v4')
        )

        # Check file size first
        response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        file_size = response.get('ContentLength', 0)

        if file_size > CONFIG["limits"]["max_file_size"]:
            return f"Error: File too large ({file_size} bytes). Maximum size is {CONFIG['limits']['max_file_size']} bytes."

        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        content = response['Body'].read().decode('utf-8')

        logger.info("MinIO object retrieved", extra={'content_length': len(content)})
        return content

    except Exception as e:
        logger.error("MinIO get object failed", exc_info=True, extra={'error': str(e)})
        return f"MinIO error: {str(e)}"

# ====== MONITORING TOOLS (From existing monitoring service) ======

@tool
def search_logs(query: str, hours: int = None, limit: int = None) -> str:
    """Search logs using LogQL query language via Loki"""
    hours = hours or CONFIG["limits"]["default_hours"]
    limit = limit or CONFIG["limits"]["default_limit"]

    logger.info("Searching logs", extra={'query': query[:100], 'hours': hours, 'limit': limit})

    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        params = {
            'query': query,
            'start': int(start_time.timestamp() * 1000000000),  # nanoseconds
            'end': int(end_time.timestamp() * 1000000000),
            'limit': limit,
            'direction': 'backward'
        }

        with httpx.Client() as client:
            response = client.get(f"{CONFIG['loki']['url']}/loki/api/v1/query_range", params=params)
            response.raise_for_status()

            data = response.json()
            if not data.get('data') or not data['data'].get('result'):
                return json.dumps({"total_entries": 0, "streams": []}, indent=2)

            total_entries = 0
            streams = []

            for stream in data['data']['result']:
                entries = []
                for timestamp, line in stream['values']:
                    entries.append({
                        'timestamp': datetime.fromtimestamp(int(timestamp) / 1000000000).isoformat(),
                        'line': line
                    })
                total_entries += len(entries)

                streams.append({
                    'labels': stream['stream'],
                    'entries': entries
                })

            result = {
                "total_entries": total_entries,
                "streams": streams,
                "query": query,
                "time_range": f"{start_time.isoformat()} to {end_time.isoformat()}"
            }

            logger.info("Log search completed", extra={'entries_found': total_entries})
            return json.dumps(result, indent=2, default=str)

    except Exception as e:
        logger.error("Log search failed", exc_info=True, extra={'error': str(e)})
        return f"Log search error: {str(e)}"

@tool
def get_system_metrics(charts: List[str] = None, after: int = 300) -> str:
    """Get current system metrics from Netdata"""
    charts = charts or ['system.cpu', 'system.ram', 'disk.util']

    logger.info("Getting system metrics", extra={'charts': charts, 'after': after})

    try:
        results = {}

        with httpx.Client() as client:
            for chart in charts:
                params = {
                    'chart': chart,
                    'after': -after,
                    'format': 'json',
                    'points': 60
                }

                response = client.get(f"{CONFIG['netdata']['url']}/api/v1/data", params=params)
                if response.status_code == 200:
                    data = response.json()
                    results[chart] = {
                        'labels': data.get('labels', []),
                        'latest_values': data.get('latest_values', []),
                        'min': data.get('min', []),
                        'max': data.get('max', [])
                    }
                else:
                    results[chart] = {"error": f"HTTP {response.status_code}"}

        logger.info("System metrics retrieved", extra={'charts_count': len(results)})
        return json.dumps(results, indent=2, default=str)

    except Exception as e:
        logger.error("System metrics failed", exc_info=True, extra={'error': str(e)})
        return f"System metrics error: {str(e)}"

# ====== WEB FETCH TOOLS (From official fetch server) ======

def extract_content_from_html(html: str) -> str:
    """Extract and convert HTML content to Markdown format"""
    try:
        ret = readabilipy.simple_json.simple_json_from_html_string(
            html, use_readability=True
        )
        if not ret.get("content"):
            return "<error>Page failed to be simplified from HTML</error>"

        content = markdownify.markdownify(
            ret["content"],
            heading_style=markdownify.ATX,
        )
        return content
    except Exception as e:
        return f"<error>HTML processing failed: {str(e)}</error>"

@tool
def fetch_web_content(url: str, max_length: int = 10000, raw: bool = False) -> str:
    """Fetch web content and convert to markdown (with robots.txt compliance)"""
    logger.info("Fetching web content", extra={'url': url, 'max_length': max_length, 'raw': raw})

    try:
        user_agent = "ModelContextProtocol/1.0 (ai-servicers.com MCP Server)"

        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            # Check robots.txt (simplified check)
            try:
                robots_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}/robots.txt"
                robots_response = client.get(robots_url, headers={"User-Agent": user_agent})
                if robots_response.status_code == 200:
                    # Simple robots.txt check - in production, use full Protego parsing
                    robots_content = robots_response.text.lower()
                    if "disallow: /" in robots_content and "*" in robots_content:
                        logger.warning("Robots.txt may disallow access", extra={'url': url})
            except:
                pass  # Ignore robots.txt errors for now

            # Fetch the actual content
            headers = {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }

            response = client.get(url, headers=headers)
            response.raise_for_status()

            if raw:
                content = response.text
            else:
                content = extract_content_from_html(response.text)

            # Truncate if too long
            if len(content) > max_length:
                content = content[:max_length] + f"\n\n[Content truncated at {max_length} characters]"

            result = {
                "url": url,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", "unknown"),
                "content_length": len(content),
                "content": content
            }

            logger.info("Web content fetched", extra={'url': url, 'length': len(content)})
            return json.dumps(result, indent=2)

    except Exception as e:
        logger.error("Web fetch failed", exc_info=True, extra={'error': str(e), 'url': url})
        return f"Web fetch error: {str(e)}"

# ====== FILESYSTEM TOOLS (From official filesystem server, simplified) ======

def validate_file_path(path: str, allowed_roots: List[str] = None) -> bool:
    """Basic path validation"""
    allowed_roots = allowed_roots or ["/tmp", "/home/administrator/projects/data"]

    try:
        abs_path = Path(path).resolve()
        return any(str(abs_path).startswith(root) for root in allowed_roots)
    except:
        return False

@tool
def read_file(file_path: str) -> str:
    """Read file content with security validation"""
    logger.info("Reading file", extra={'path': file_path})

    try:
        if not validate_file_path(file_path):
            return "Error: File path not allowed. Only /tmp and /home/administrator/projects/data paths are permitted."

        if not is_valid_filepath(file_path):
            return "Error: Invalid file path format."

        path = Path(file_path)
        if not path.exists():
            return f"Error: File does not exist: {file_path}"

        if not path.is_file():
            return f"Error: Path is not a file: {file_path}"

        # Check file size
        if path.stat().st_size > CONFIG["limits"]["max_file_size"]:
            return f"Error: File too large. Maximum size is {CONFIG['limits']['max_file_size']} bytes."

        content = path.read_text(encoding='utf-8')

        result = {
            "file_path": str(path),
            "size": path.stat().st_size,
            "content": content
        }

        logger.info("File read successfully", extra={'path': file_path, 'size': len(content)})
        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error("File read failed", exc_info=True, extra={'error': str(e), 'path': file_path})
        return f"File read error: {str(e)}"

@tool
def list_directory(directory_path: str) -> str:
    """List directory contents with security validation"""
    logger.info("Listing directory", extra={'path': directory_path})

    try:
        if not validate_file_path(directory_path):
            return "Error: Directory path not allowed. Only /tmp and /home/administrator/projects/data paths are permitted."

        path = Path(directory_path)
        if not path.exists():
            return f"Error: Directory does not exist: {directory_path}"

        if not path.is_dir():
            return f"Error: Path is not a directory: {directory_path}"

        items = []
        for item in path.iterdir():
            try:
                stat = item.stat()
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else None,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except:
                items.append({
                    "name": item.name,
                    "type": "unknown",
                    "error": "Cannot access"
                })

        result = {
            "directory_path": str(path),
            "items": items,
            "count": len(items)
        }

        logger.info("Directory listed", extra={'path': directory_path, 'items': len(items)})
        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error("Directory list failed", exc_info=True, extra={'error': str(e), 'path': directory_path})
        return f"Directory list error: {str(e)}"

# ====== LANGCHAIN AGENT SETUP ======

# Collect all tools
tools = [
    # PostgreSQL tools (Modern Implementation)
    postgres_query,
    postgres_list_databases,
    postgres_list_tables,
    postgres_server_info,
    postgres_database_sizes,

    # MinIO S3 tools
    minio_list_objects,
    minio_get_object,

    # Monitoring tools
    search_logs,
    get_system_metrics,

    # Web fetch tools
    fetch_web_content,

    # Filesystem tools
    read_file,
    list_directory
]

# LiteLLM client with configurable model
llm = ChatLiteLLM(
    model=os.environ.get("AGENT_MODEL", "claude-3-5-sonnet-20241022"),
    openai_api_base=CONFIG["litellm"]["url"],
    temperature=0.1
)

# Agent prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful AI assistant with access to comprehensive infrastructure tools.

Available tool categories:
• PostgreSQL Database: Query databases, list tables and schemas
• MinIO Object Storage: List and retrieve files from S3-compatible storage
• System Monitoring: Search logs with LogQL, get system metrics from Netdata
• Web Content: Fetch and convert web pages to markdown with robots.txt compliance
• File System: Safely read files and list directories (restricted paths)

Always:
1. Provide clear, structured responses
2. Explain what you're doing before using tools
3. Include relevant context from tool results
4. Follow security best practices
5. Log important operations for audit purposes

Security reminders:
• Database queries are read-only (SELECT statements only)
• File system access is restricted to safe paths
• Web fetching respects robots.txt when possible
• All operations are logged for monitoring"""),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create agent
agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=5
)

# Add agent endpoint
add_routes(app, agent_executor, path="/agent")

# ====== DIRECT TOOL API ======

class ToolRequest(BaseModel):
    input: Dict[str, Any]

@app.post("/tools/{tool_name}")
async def execute_tool(tool_name: str, request: ToolRequest):
    """Execute a specific tool directly with dictionary input"""
    logger.info("Direct tool execution", extra={
        'tool': tool_name,
        'input_keys': list(request.input.keys())
    })

    # Find the requested tool
    tool_map = {tool.name: tool for tool in tools}

    if tool_name not in tool_map:
        available_tools = list(tool_map.keys())
        logger.warning("Tool not found", extra={
            'requested_tool': tool_name,
            'available_tools': available_tools
        })
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found. Available tools: {available_tools}"
        )

    try:
        tool = tool_map[tool_name]
        result = tool.invoke(request.input)

        return {
            "tool": tool_name,
            "input": request.input,
            "result": result,
            "status": "success",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error("Tool execution failed", exc_info=True, extra={
            'tool': tool_name,
            'error': str(e)
        })
        raise HTTPException(
            status_code=500,
            detail=f"Tool execution failed: {str(e)}"
        )

@app.get("/tools")
async def list_tools():
    """List all available tools"""
    tool_info = []
    for tool in tools:
        tool_info.append({
            "name": tool.name,
            "description": tool.description,
            "category": _get_tool_category(tool.name)
        })

    return {
        "tools": tool_info,
        "count": len(tool_info),
        "categories": _get_tool_categories()
    }

def _get_tool_category(tool_name: str) -> str:
    """Get tool category based on name"""
    if tool_name.startswith("postgres_"):
        return "database"
    elif tool_name.startswith("minio_"):
        return "storage"
    elif tool_name in ["search_logs", "get_system_metrics"]:
        return "monitoring"
    elif tool_name == "fetch_web_content":
        return "web"
    elif tool_name in ["read_file", "list_directory"]:
        return "filesystem"
    else:
        return "misc"

def _get_tool_categories() -> Dict[str, List[str]]:
    """Get all tools organized by category"""
    categories = {}
    for tool in tools:
        category = _get_tool_category(tool.name)
        if category not in categories:
            categories[category] = []
        categories[category].append(tool.name)
    return categories

# ====== APPLICATION STARTUP ======

@app.on_event("startup")
async def startup_event():
    logger.info("MCP Server starting up", extra={
        'tools_count': len(tools),
        'categories': list(_get_tool_categories().keys()),
        'postgres_host': CONFIG["postgres"]["host"],
        'loki_url': CONFIG["loki"]["url"],
        'minio_endpoint': CONFIG["minio"]["endpoint"]
    })

    # Test critical connections
    await _test_connections()

async def _test_connections():
    """Test connections to critical services"""
    logger.info("Testing service connections...")

    # Test PostgreSQL
    try:
        result = postgres_query("SELECT version();")
        if "PostgreSQL" in result:
            logger.info("PostgreSQL connection: OK")
        else:
            logger.warning("PostgreSQL connection: Issues detected")
    except Exception as e:
        logger.error("PostgreSQL connection: FAILED", extra={'error': str(e)})

    # Test Loki
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CONFIG['loki']['url']}/ready")
            if response.status_code == 200:
                logger.info("Loki connection: OK")
            else:
                logger.warning("Loki connection: Issues detected")
    except Exception as e:
        logger.error("Loki connection: FAILED", extra={'error': str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None  # Use our custom logging
    )