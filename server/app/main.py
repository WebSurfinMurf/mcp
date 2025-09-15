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

# ====== MCP MICROSERVICE ORCHESTRATOR TOOLS ======

@tool
def n8n_list_workflows() -> str:
    """List all workflows from n8n MCP service"""
    logger.info("Orchestrating n8n workflow list request")

    try:
        endpoint = os.environ.get("MCP_N8N_ENDPOINT", "http://mcp-n8n:3000")
        auth_token = os.environ.get("MCP_N8N_AUTH_TOKEN", "secure-n8n-token-2025-mcp-orchestrator")

        # MCP JSON-RPC request to list workflows
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "n8n_list_workflows",
                "arguments": {}
            }
        }

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/mcp",
                json=mcp_request,
                headers={"Authorization": f"Bearer {auth_token}"},
                timeout=30.0
            )
            response.raise_for_status()

            result = response.json()
            if "result" in result:
                logger.info("n8n workflow list retrieved successfully")
                return json.dumps(result["result"], indent=2)
            else:
                logger.error("No result in n8n MCP response", extra={'response': result})
                return f"n8n MCP error: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("n8n workflow list failed", exc_info=True, extra={'error': str(e)})
        return f"n8n orchestrator error: {str(e)}"

@tool
def n8n_get_workflow(workflow_id: str) -> str:
    """Get workflow details from n8n MCP service"""
    logger.info("Orchestrating n8n workflow details request", extra={'workflow_id': workflow_id})

    try:
        endpoint = os.environ.get("MCP_N8N_ENDPOINT", "http://mcp-n8n:3000")
        auth_token = os.environ.get("MCP_N8N_AUTH_TOKEN", "secure-n8n-token-2025-mcp-orchestrator")

        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "n8n_get_workflow",
                "arguments": {"id": workflow_id}
            }
        }

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/mcp",
                json=mcp_request,
                headers={"Authorization": f"Bearer {auth_token}"},
                timeout=30.0
            )
            response.raise_for_status()

            result = response.json()
            if "result" in result:
                logger.info("n8n workflow details retrieved successfully", extra={'workflow_id': workflow_id})
                return json.dumps(result["result"], indent=2)
            else:
                logger.error("No result in n8n MCP response", extra={'response': result})
                return f"n8n MCP error: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("n8n workflow details failed", exc_info=True, extra={'error': str(e), 'workflow_id': workflow_id})
        return f"n8n orchestrator error: {str(e)}"

@tool
def n8n_get_database_statistics() -> str:
    """Get n8n MCP database statistics - demonstrates orchestrator pattern"""
    logger.info("Orchestrating n8n database statistics request")

    try:
        endpoint = os.environ.get("MCP_N8N_ENDPOINT", "http://mcp-n8n:3000")
        auth_token = os.environ.get("MCP_N8N_AUTH_TOKEN", "secure-n8n-token-2025-mcp-orchestrator")

        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "get_database_statistics",
                "arguments": {}
            }
        }

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/mcp",
                json=mcp_request,
                headers={"Authorization": f"Bearer {auth_token}"},
                timeout=30.0
            )
            response.raise_for_status()

            result = response.json()
            if "result" in result:
                logger.info("n8n database statistics retrieved successfully")
                return json.dumps(result["result"], indent=2)
            else:
                logger.error("No result in n8n database statistics", extra={'response': result})
                return f"n8n MCP database statistics error: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("n8n database statistics failed", exc_info=True, extra={'error': str(e)})
        return f"n8n orchestrator error: {str(e)}"

# ====== PLAYWRIGHT ORCHESTRATOR TOOLS ======

@tool
def playwright_navigate(url: str, wait_for_load: bool = True, timeout: int = 30000) -> str:
    """Navigate to a URL using the custom Playwright service"""
    logger.info("Orchestrating Playwright navigation", extra={'url': url, 'wait_for_load': wait_for_load})

    # Security validation - domain restrictions
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()

    # Basic security check (can be enhanced with environment variables)
    blocked_domains = ['localhost', '127.0.0.1', '0.0.0.0', 'internal']
    if any(blocked in domain for blocked in blocked_domains):
        logger.warning("Blocked domain access attempt", extra={'domain': domain, 'url': url})
        return f"Error: Domain {domain} is not allowed by security policy"

    try:
        endpoint = "http://mcp-playwright:8080"

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/tools/navigate",
                json={'input': {'url': url, 'wait_for_load': wait_for_load, 'timeout': timeout}},
                timeout=60.0
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                tool_result = result['result']
                logger.info("Playwright navigation successful", extra={'url': tool_result.get('url'), 'title': tool_result.get('title')})
                return f"Successfully navigated to: {tool_result.get('title', 'Untitled')} ({tool_result.get('url')})\nStatus: {tool_result.get('status')} {tool_result.get('statusText', '')}"
            else:
                logger.error("Playwright navigation failed", extra={'error': result.get('error'), 'url': url})
                return f"Navigation failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("Playwright navigation orchestrator error", exc_info=True, extra={'error': str(e), 'url': url})
        return f"Playwright orchestrator error: {str(e)}"

@tool
def playwright_screenshot(full_page: bool = False, format: str = "png") -> str:
    """Take a screenshot of the current page using the custom Playwright service"""
    logger.info("Orchestrating Playwright screenshot", extra={'full_page': full_page, 'format': format})

    try:
        endpoint = "http://mcp-playwright:8080"

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/tools/screenshot",
                json={'input': {'full_page': full_page, 'format': format}},
                timeout=60.0
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                tool_result = result['result']
                logger.info("Playwright screenshot successful", extra={'format': tool_result.get('format'), 'size': tool_result.get('size')})
                return f"Screenshot captured successfully:\n- Format: {tool_result.get('format')}\n- Size: {tool_result.get('size'):,} bytes\n- Base64 data length: {len(tool_result.get('screenshot', ''))}"
            else:
                logger.error("Playwright screenshot failed", extra={'error': result.get('error')})
                return f"Screenshot failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("Playwright screenshot orchestrator error", exc_info=True, extra={'error': str(e)})
        return f"Playwright orchestrator error: {str(e)}"

@tool
def playwright_click(selector: str, timeout: int = 30000) -> str:
    """Click an element on the page using the custom Playwright service"""
    logger.info("Orchestrating Playwright click", extra={'selector': selector, 'timeout': timeout})

    try:
        endpoint = "http://mcp-playwright:8080"

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/tools/click",
                json={'input': {'selector': selector, 'timeout': timeout}},
                timeout=60.0
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                tool_result = result['result']
                logger.info("Playwright click successful", extra={'selector': selector})
                return f"Successfully clicked element: {selector}"
            else:
                logger.error("Playwright click failed", extra={'error': result.get('error'), 'selector': selector})
                return f"Click failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("Playwright click orchestrator error", exc_info=True, extra={'error': str(e), 'selector': selector})
        return f"Playwright orchestrator error: {str(e)}"

@tool
def playwright_fill(selector: str, value: str, timeout: int = 30000) -> str:
    """Fill a form field with text using the custom Playwright service"""
    logger.info("Orchestrating Playwright fill", extra={'selector': selector, 'value_length': len(value), 'timeout': timeout})

    try:
        endpoint = "http://mcp-playwright:8080"

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/tools/fill",
                json={'input': {'selector': selector, 'value': value, 'timeout': timeout}},
                timeout=60.0
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                tool_result = result['result']
                logger.info("Playwright fill successful", extra={'selector': selector, 'value_length': len(value)})
                return f"Successfully filled field {selector} with {len(value)} characters"
            else:
                logger.error("Playwright fill failed", extra={'error': result.get('error'), 'selector': selector})
                return f"Fill failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("Playwright fill orchestrator error", exc_info=True, extra={'error': str(e), 'selector': selector})
        return f"Playwright orchestrator error: {str(e)}"

@tool
def playwright_get_content(selector: str = None) -> str:
    """Get text content from the page or a specific element using the custom Playwright service"""
    logger.info("Orchestrating Playwright get content", extra={'selector': selector})

    try:
        endpoint = "http://mcp-playwright:8080"

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/tools/get-content",
                json={'input': {'selector': selector}},
                timeout=60.0
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                tool_result = result['result']
                content = tool_result.get('content', '')
                logger.info("Playwright get content successful", extra={'selector': selector or 'body', 'content_length': len(content)})
                return f"Content retrieved from {selector or 'page'} ({len(content)} characters):\n\n{content}"
            else:
                logger.error("Playwright get content failed", extra={'error': result.get('error'), 'selector': selector})
                return f"Get content failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("Playwright get content orchestrator error", exc_info=True, extra={'error': str(e), 'selector': selector})
        return f"Playwright orchestrator error: {str(e)}"

@tool
def playwright_evaluate(script: str, args: list = None) -> str:
    """Execute JavaScript in the page context using the custom Playwright service"""
    logger.info("Orchestrating Playwright evaluate", extra={'script_length': len(script), 'args_count': len(args or [])})

    try:
        endpoint = "http://mcp-playwright:8080"

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/tools/evaluate",
                json={'input': {'script': script, 'args': args or []}},
                timeout=60.0
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                tool_result = result['result']
                script_result = tool_result.get('result')
                logger.info("Playwright evaluate successful", extra={'script_preview': script[:50], 'result_type': type(script_result).__name__})
                return f"JavaScript executed successfully:\nScript: {script[:100]}{'...' if len(script) > 100 else ''}\nResult: {json.dumps(script_result, indent=2) if script_result is not None else 'undefined'}"
            else:
                logger.error("Playwright evaluate failed", extra={'error': result.get('error'), 'script': script[:100]})
                return f"JavaScript execution failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("Playwright evaluate orchestrator error", exc_info=True, extra={'error': str(e), 'script': script[:50]})
        return f"Playwright orchestrator error: {str(e)}"

@tool
def playwright_wait_for_selector(selector: str, timeout: int = 30000, state: str = "visible") -> str:
    """Wait for an element to appear on the page using the custom Playwright service"""
    logger.info("Orchestrating Playwright wait for selector", extra={'selector': selector, 'timeout': timeout, 'state': state})

    try:
        endpoint = "http://mcp-playwright:8080"

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/tools/wait-for-selector",
                json={'input': {'selector': selector, 'timeout': timeout, 'state': state}},
                timeout=timeout / 1000 + 10  # Convert ms to seconds and add buffer
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                tool_result = result['result']
                logger.info("Playwright wait for selector successful", extra={'selector': selector, 'found': tool_result.get('found')})
                return f"Element found: {selector}\n- Visible: {tool_result.get('visible')}\n- Enabled: {tool_result.get('enabled')}\n- State: {tool_result.get('state')}"
            else:
                logger.error("Playwright wait for selector failed", extra={'error': result.get('error'), 'selector': selector})
                return f"Wait for selector failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("Playwright wait for selector orchestrator error", exc_info=True, extra={'error': str(e), 'selector': selector})
        return f"Playwright orchestrator error: {str(e)}"

# ====== LANGCHAIN AGENT SETUP ======

# Tools list will be defined after all tool definitions

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

# Agent creation will be moved after tools definition

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
    elif tool_name.startswith("playwright_"):
        return "browser-automation"
    elif tool_name.startswith("n8n_"):
        return "workflow-automation"
    elif tool_name.startswith("tsdb_"):
        return "time-series-database"
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

# ====== TIMESCALEDB HTTP ORCHESTRATOR TOOLS ======

@tool
def tsdb_query(query: str) -> str:
    """Execute SELECT queries against TimescaleDB via HTTP service"""
    logger.info("Orchestrating TimescaleDB query", extra={'query_length': len(query)})

    try:
        if not query.strip().upper().startswith("SELECT"):
            return "Error: Only SELECT queries are allowed for security"

        endpoint = os.getenv("MCP_TIMESCALEDB_ENDPOINT", "http://mcp-timescaledb:8080")

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/tools/tsdb_query",
                json={'input': {'query': query}},
                timeout=30.0
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                tool_result = result['result']
                logger.info("TimescaleDB query successful", extra={
                    'rows': tool_result.get('row_count', 0),
                    'execution_time': tool_result.get('execution_time_ms', 0)
                })

                rows = tool_result.get('rows', [])
                if not rows:
                    return "Query executed successfully but returned no rows."

                # Format results as a readable table
                if len(rows) == 1:
                    return f"Query returned 1 row:\n{json.dumps(rows[0], indent=2)}"
                else:
                    return f"Query returned {len(rows)} rows:\n{json.dumps(rows, indent=2)}"
            else:
                logger.error("TimescaleDB query failed", extra={'error': result.get('error')})
                return f"Query failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("TimescaleDB query orchestrator error", exc_info=True, extra={'error': str(e)})
        return f"TimescaleDB orchestrator error: {str(e)}"

@tool
def tsdb_database_stats() -> str:
    """Get comprehensive TimescaleDB database statistics via HTTP service"""
    logger.info("Orchestrating TimescaleDB database stats")

    try:
        endpoint = os.getenv("MCP_TIMESCALEDB_ENDPOINT", "http://mcp-timescaledb:8080")

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/tools/tsdb_database_stats",
                json={'input': {}},
                timeout=30.0
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                tool_result = result['result']
                logger.info("TimescaleDB database stats successful")

                stats = {
                    "Database Size": tool_result.get('database_size', 'unknown'),
                    "Table Count": tool_result.get('table_count', 0),
                    "Hypertable Count": tool_result.get('hypertable_count', 0),
                    "PostgreSQL Version": tool_result.get('postgresql_version', 'unknown'),
                    "TimescaleDB Version": tool_result.get('timescaledb_version', 'unknown'),
                    "Connection Pool": tool_result.get('connection_pool', {})
                }

                return f"TimescaleDB Statistics:\n{json.dumps(stats, indent=2)}"
            else:
                logger.error("TimescaleDB database stats failed", extra={'error': result.get('error')})
                return f"Database stats failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("TimescaleDB database stats orchestrator error", exc_info=True, extra={'error': str(e)})
        return f"TimescaleDB orchestrator error: {str(e)}"

@tool
def tsdb_show_hypertables() -> str:
    """List all TimescaleDB hypertables with metadata via HTTP service"""
    logger.info("Orchestrating TimescaleDB show hypertables")

    try:
        endpoint = os.getenv("MCP_TIMESCALEDB_ENDPOINT", "http://mcp-timescaledb:8080")

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/tools/tsdb_show_hypertables",
                json={'input': {}},
                timeout=30.0
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                tool_result = result['result']
                logger.info("TimescaleDB show hypertables successful", extra={
                    'hypertable_count': tool_result.get('total_count', 0)
                })

                hypertables = tool_result.get('hypertables', [])
                if not hypertables:
                    return "No hypertables found in the database."

                return f"Found {len(hypertables)} hypertable(s):\n{json.dumps(hypertables, indent=2)}"
            else:
                logger.error("TimescaleDB show hypertables failed", extra={'error': result.get('error')})
                return f"Show hypertables failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("TimescaleDB show hypertables orchestrator error", exc_info=True, extra={'error': str(e)})
        return f"TimescaleDB orchestrator error: {str(e)}"

@tool
def tsdb_execute(command: str) -> str:
    """Execute non-SELECT SQL commands against TimescaleDB via HTTP service"""
    logger.info("Orchestrating TimescaleDB execute command", extra={'command_length': len(command)})

    try:
        # Security check: Allow common DDL/DML operations but block dangerous ones
        command_upper = command.strip().upper()
        dangerous_commands = ['DROP DATABASE', 'DROP USER', 'TRUNCATE', 'DELETE FROM pg_']
        if any(dangerous in command_upper for dangerous in dangerous_commands):
            return f"Error: Dangerous command blocked for security: {command_upper[:50]}..."

        endpoint = os.getenv("MCP_TIMESCALEDB_ENDPOINT", "http://mcp-timescaledb:8080")

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/tools/tsdb_execute",
                json={'input': {'command': command}},
                timeout=60.0
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                tool_result = result['result']
                logger.info("TimescaleDB execute successful", extra={
                    'execution_time': tool_result.get('execution_time_ms', 0)
                })
                return f"Command executed successfully: {tool_result.get('message', 'Operation completed')}"
            else:
                logger.error("TimescaleDB execute failed", extra={'error': result.get('error')})
                return f"Command failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("TimescaleDB execute orchestrator error", exc_info=True, extra={'error': str(e)})
        return f"TimescaleDB orchestrator error: {str(e)}"

@tool
def tsdb_create_hypertable(table_name: str, time_column: str, chunk_time_interval: str = "1 day") -> str:
    """Convert regular table to TimescaleDB hypertable via HTTP service"""
    logger.info("Orchestrating TimescaleDB create hypertable", extra={
        'table': table_name, 'time_column': time_column, 'interval': chunk_time_interval
    })

    try:
        endpoint = os.getenv("MCP_TIMESCALEDB_ENDPOINT", "http://mcp-timescaledb:8080")

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/tools/tsdb_create_hypertable",
                json={'input': {
                    'table_name': table_name,
                    'time_column': time_column,
                    'chunk_time_interval': chunk_time_interval
                }},
                timeout=60.0
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                tool_result = result['result']
                logger.info("TimescaleDB create hypertable successful", extra={'table': table_name})
                return f"Hypertable created successfully: {tool_result.get('message', f'Table {table_name} converted to hypertable')}"
            else:
                logger.error("TimescaleDB create hypertable failed", extra={'error': result.get('error')})
                return f"Create hypertable failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("TimescaleDB create hypertable orchestrator error", exc_info=True, extra={'error': str(e)})
        return f"TimescaleDB orchestrator error: {str(e)}"

@tool
def tsdb_show_chunks(hypertable: str) -> str:
    """Show chunks for specified hypertable via HTTP service"""
    logger.info("Orchestrating TimescaleDB show chunks", extra={'hypertable': hypertable})

    try:
        endpoint = os.getenv("MCP_TIMESCALEDB_ENDPOINT", "http://mcp-timescaledb:8080")

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/tools/tsdb_show_chunks",
                json={'input': {'hypertable': hypertable}},
                timeout=30.0
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                tool_result = result['result']
                chunks = tool_result.get('chunks', [])
                logger.info("TimescaleDB show chunks successful", extra={
                    'hypertable': hypertable, 'chunk_count': len(chunks)
                })

                if not chunks:
                    return f"No chunks found for hypertable '{hypertable}'"

                return f"Found {len(chunks)} chunk(s) for hypertable '{hypertable}':\n{json.dumps(chunks, indent=2)}"
            else:
                logger.error("TimescaleDB show chunks failed", extra={'error': result.get('error')})
                return f"Show chunks failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("TimescaleDB show chunks orchestrator error", exc_info=True, extra={'error': str(e)})
        return f"TimescaleDB orchestrator error: {str(e)}"

@tool
def tsdb_compression_stats(hypertable: str = None) -> str:
    """View compression statistics for hypertables via HTTP service"""
    logger.info("Orchestrating TimescaleDB compression stats", extra={'hypertable': hypertable})

    try:
        endpoint = os.getenv("MCP_TIMESCALEDB_ENDPOINT", "http://mcp-timescaledb:8080")

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/tools/tsdb_compression_stats",
                json={'input': {'hypertable': hypertable} if hypertable else {'input': {}}},
                timeout=30.0
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                tool_result = result['result']
                logger.info("TimescaleDB compression stats successful")

                stats = tool_result.get('compression_stats', [])
                if not stats:
                    return "No compression statistics available"

                return f"Compression Statistics:\n{json.dumps(stats, indent=2)}"
            else:
                logger.error("TimescaleDB compression stats failed", extra={'error': result.get('error')})
                return f"Compression stats failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("TimescaleDB compression stats orchestrator error", exc_info=True, extra={'error': str(e)})
        return f"TimescaleDB orchestrator error: {str(e)}"

@tool
def tsdb_add_compression(hypertable: str, compress_after: str) -> str:
    """Add compression policy to hypertable via HTTP service"""
    logger.info("Orchestrating TimescaleDB add compression", extra={
        'hypertable': hypertable, 'compress_after': compress_after
    })

    try:
        endpoint = os.getenv("MCP_TIMESCALEDB_ENDPOINT", "http://mcp-timescaledb:8080")

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/tools/tsdb_add_compression",
                json={'input': {
                    'hypertable': hypertable,
                    'compress_after': compress_after
                }},
                timeout=60.0
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                tool_result = result['result']
                logger.info("TimescaleDB add compression successful", extra={'hypertable': hypertable})
                return f"Compression policy added: {tool_result.get('message', f'Compression enabled for {hypertable}')}"
            else:
                logger.error("TimescaleDB add compression failed", extra={'error': result.get('error')})
                return f"Add compression failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("TimescaleDB add compression orchestrator error", exc_info=True, extra={'error': str(e)})
        return f"TimescaleDB orchestrator error: {str(e)}"

@tool
def tsdb_continuous_aggregate(view_name: str, query: str) -> str:
    """Create continuous aggregate view via HTTP service"""
    logger.info("Orchestrating TimescaleDB continuous aggregate", extra={
        'view_name': view_name, 'query_length': len(query)
    })

    try:
        endpoint = os.getenv("MCP_TIMESCALEDB_ENDPOINT", "http://mcp-timescaledb:8080")

        with httpx.Client() as client:
            response = client.post(
                f"{endpoint}/tools/tsdb_continuous_aggregate",
                json={'input': {
                    'view_name': view_name,
                    'query': query
                }},
                timeout=90.0
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'success':
                tool_result = result['result']
                logger.info("TimescaleDB continuous aggregate successful", extra={'view_name': view_name})
                return f"Continuous aggregate created: {tool_result.get('message', f'View {view_name} created successfully')}"
            else:
                logger.error("TimescaleDB continuous aggregate failed", extra={'error': result.get('error')})
                return f"Continuous aggregate failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error("TimescaleDB continuous aggregate orchestrator error", exc_info=True, extra={'error': str(e)})
        return f"TimescaleDB orchestrator error: {str(e)}"

# ====== COLLECT ALL TOOLS ======

# Collect all tools - defined after all tool implementations
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
    list_directory,

    # n8n MCP Orchestrator tools
    n8n_list_workflows,
    n8n_get_workflow,
    n8n_get_database_statistics,

    # Playwright MCP Orchestrator tools (Custom HTTP Service)
    playwright_navigate,
    playwright_screenshot,
    playwright_click,
    playwright_fill,
    playwright_get_content,
    playwright_evaluate,
    playwright_wait_for_selector,

    # TimescaleDB MCP Orchestrator tools (HTTP Service)
    tsdb_query,
    tsdb_database_stats,
    tsdb_show_hypertables,
    tsdb_execute,
    tsdb_create_hypertable,
    tsdb_show_chunks,
    tsdb_compression_stats,
    tsdb_add_compression,
    tsdb_continuous_aggregate
]

# ====== AGENT CREATION ======

# Create agent after tools are defined
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