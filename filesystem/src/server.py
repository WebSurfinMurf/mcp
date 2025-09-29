"""
MCP Filesystem Server
Provides file system operations via SSE MCP endpoint
"""
import os
import json
import asyncio
import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError

# Configure logging if not already set by container runtime
logging.basicConfig(level=logging.INFO)
import aiofiles

app = FastAPI(title="MCP Filesystem Server", version="1.0.0")

# Configuration
WORKSPACE_PATH = os.getenv("WORKSPACE_PATH", "/workspace")
TEMP_PATH = os.getenv("TEMP_PATH", "/tmp")
MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "filesystem")


@dataclass
class SessionState:
    """Track active SSE client sessions."""

    queue: asyncio.Queue[Dict[str, str]] = field(default_factory=asyncio.Queue)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


SESSIONS: Dict[str, SessionState] = {}
logger = logging.getLogger("mcp-filesystem")

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

class MCPTools:
    """MCP tool implementations for filesystem operations"""

    @staticmethod
    async def list_files(path: str = "", show_hidden: bool = False) -> Dict[str, Any]:
        """List files and directories"""
        try:
            if path == "" or path == ".":
                full_path = Path(WORKSPACE_PATH)
            elif path.startswith('/'):
                # Absolute path - check if it's within workspace
                full_path = Path(path)
                workspace_path = Path(WORKSPACE_PATH).resolve()

                # Check if the path starts with /home/administrator/projects (the host path)
                if path.startswith('/home/administrator/projects/'):
                    # Convert host path to container path
                    relative_part = path[len('/home/administrator/projects/'):]
                    full_path = workspace_path / relative_part
                else:
                    try:
                        full_path.resolve().relative_to(workspace_path)
                    except ValueError:
                        return {"error": f"Access denied: Path outside workspace: {path}"}
            else:
                # Relative path - prepend workspace
                full_path = Path(WORKSPACE_PATH) / path


            if not full_path.exists():
                return {"error": f"Path does not exist: {path} (full_path: {full_path})"}

            items = []
            for item in full_path.iterdir():
                if not show_hidden and item.name.startswith('.'):
                    continue

                try:
                    stat = item.stat()
                    file_type = "directory" if item.is_dir() else "file"
                    size = stat.st_size if item.is_file() else None
                    modified = stat.st_mtime
                except (OSError, FileNotFoundError):
                    # Handle broken symlinks or inaccessible files
                    file_type = "link" if item.is_symlink() else "unknown"
                    size = None
                    modified = None

                items.append({
                    "name": item.name,
                    "type": file_type,
                    "size": size,
                    "modified": modified,
                    "path": str(item.relative_to(Path(WORKSPACE_PATH)))
                })

            return {
                "path": path,
                "items": sorted(items, key=lambda x: (x["type"] == "file", x["name"]))
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    async def read_file(path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """Read file contents"""
        try:
            # Handle both absolute and relative paths
            if path.startswith('/'):
                # Absolute path - check if it's within workspace
                workspace_path = Path(WORKSPACE_PATH).resolve()

                # Check if the path starts with /home/administrator/projects (the host path)
                if path.startswith('/home/administrator/projects/'):
                    # Convert host path to container path
                    relative_part = path[len('/home/administrator/projects/'):]
                    full_path = workspace_path / relative_part
                else:
                    full_path = Path(path)
                    try:
                        full_path.resolve().relative_to(workspace_path)
                    except ValueError:
                        return {"error": f"Access denied: Path outside workspace: {path}"}
            else:
                # Relative path - prepend workspace
                full_path = Path(WORKSPACE_PATH) / path

            if not full_path.exists():
                return {"error": f"File does not exist: {path}"}

            if not full_path.is_file():
                return {"error": f"Path is not a file: {path}"}

            async with aiofiles.open(full_path, 'r', encoding=encoding) as f:
                content = await f.read()

            return {
                "path": path,
                "content": content,
                "size": len(content),
                "encoding": encoding
            }
        except UnicodeDecodeError:
            return {"error": f"Cannot decode file with {encoding} encoding"}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    async def write_file(path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """Write file contents"""
        try:
            # Only allow writing to temp directory for security
            if not path.startswith("temp/"):
                full_path = Path(TEMP_PATH) / Path(path).name
            else:
                full_path = Path(TEMP_PATH) / path.removeprefix("temp/")

            # Create directory if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(full_path, 'w', encoding=encoding) as f:
                await f.write(content)

            return {
                "path": str(full_path),
                "size": len(content),
                "encoding": encoding,
                "status": "written"
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    async def get_file_info(path: str) -> Dict[str, Any]:
        """Get file/directory information"""
        try:
            # Handle both absolute and relative paths
            if path.startswith('/'):
                # Absolute path - check if it's within workspace
                workspace_path = Path(WORKSPACE_PATH).resolve()

                # Check if the path starts with /home/administrator/projects (the host path)
                if path.startswith('/home/administrator/projects/'):
                    # Convert host path to container path
                    relative_part = path[len('/home/administrator/projects/'):]
                    full_path = workspace_path / relative_part
                else:
                    full_path = Path(path)
                    try:
                        full_path.resolve().relative_to(workspace_path)
                    except ValueError:
                        return {"error": f"Access denied: Path outside workspace: {path}"}
            else:
                # Relative path - prepend workspace
                full_path = Path(WORKSPACE_PATH) / path

            if not full_path.exists():
                return {"error": f"Path does not exist: {path}"}

            stat = full_path.stat()
            return {
                "path": path,
                "type": "directory" if full_path.is_dir() else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "permissions": oct(stat.st_mode)[-3:],
                "absolute_path": str(full_path)
            }
        except Exception as e:
            return {"error": str(e)}

async def handle_mcp_request(request: MCPRequest) -> MCPResponse:
    """Handle MCP method calls"""

    if request.method == "initialize":
        return MCPResponse(
            result={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "prompts": {},
                    "resources": {}
                },
                "serverInfo": {
                    "name": MCP_SERVER_NAME,
                    "version": "1.0.0"
                }
            },
            id=request.id
        )

    elif request.method == "tools/list":
        tools = [
            {
                "name": "list_files",
                "description": "List files and directories in workspace",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path (default: current)"},
                        "show_hidden": {"type": "boolean", "description": "Show hidden files"}
                    }
                }
            },
            {
                "name": "read_file",
                "description": "Read file contents from workspace",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to read"},
                        "encoding": {"type": "string", "description": "File encoding (default: utf-8)"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "write_file",
                "description": "Write file to temp directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to write"},
                        "content": {"type": "string", "description": "File content"},
                        "encoding": {"type": "string", "description": "File encoding (default: utf-8)"}
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "get_file_info",
                "description": "Get file/directory information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to inspect"}
                    },
                    "required": ["path"]
                }
            }
        ]

        return MCPResponse(result={"tools": tools}, id=request.id)

    elif request.method == "tools/call":
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})

        if tool_name == "list_files":
            result = await MCPTools.list_files(**arguments)
        elif tool_name == "read_file":
            result = await MCPTools.read_file(**arguments)
        elif tool_name == "write_file":
            result = await MCPTools.write_file(**arguments)
        elif tool_name == "get_file_info":
            result = await MCPTools.get_file_info(**arguments)
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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": MCP_SERVER_NAME,
        "workspace": WORKSPACE_PATH,
        "temp": TEMP_PATH
    }

@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for MCP communication following MCP SSE spec."""

    session_id = uuid.uuid4().hex
    sessions_state = SessionState()
    SESSIONS[session_id] = sessions_state

    base_url = str(request.base_url).rstrip("/")
    message_url = f"{base_url}/messages?sessionId={session_id}"

    async def event_stream():
        try:
            # Protocol handshake
            handshake = {"version": "2025-06-18"}
            yield f"event: mcp-protocol-version\ndata: {json.dumps(handshake)}\n\n"
            logger.info("SSE session %s sent protocol handshake", session_id)

            # Hint for the message endpoint (comment so Claude ignores it)
            yield f": message-endpoint {message_url}\n\n"
            logger.info("SSE session %s advertised endpoint %s", session_id, message_url)

            while True:
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(sessions_state.queue.get(), timeout=30)
                    event_name = event.get("event", "mcp-json-rpc-2.0")
                    data = event.get("data", "")
                    logger.info("SSE session %s sending event %s", session_id, event_name)
                    yield f"event: {event_name}\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive comment to prevent idle disconnects
                    yield ":keepalive\n\n"
        finally:
            SESSIONS.pop(session_id, None)
            logger.info("SSE session %s closed", session_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
    )


@app.post("/messages", name="mcp_message")
async def mcp_message(request: Request):
    """Receive JSON-RPC requests from SSE clients and stream responses."""

    session_id = request.query_params.get("sessionId")
    session = SESSIONS.get(session_id) if session_id else None
    if not session:
        raise HTTPException(status_code=404, detail="Unknown or expired session")

    try:
        payload = await request.json()
        mcp_request = MCPRequest(**payload)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid MCP request: {exc}")

    logger.info("Received MCP request %s for session %s", mcp_request.method, session_id)
    response = await handle_mcp_request(mcp_request)

    response_dict = json.loads(response.model_dump_json())
    await session.queue.put({
        "event": "mcp-json-rpc-2.0",
        "data": json.dumps(response_dict)
    })
    logger.info("Queued response event for session %s", session_id)

    if mcp_request.method == "initialize":
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/tools/list_changed",
            "params": {}
        }
        await session.queue.put({
            "event": "mcp-json-rpc-2.0",
            "data": json.dumps(notification)
        })
        logger.info("Queued tools/list_changed notification for session %s", session_id)

    return response_dict

@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """HTTP POST endpoint for MCP requests"""
    response = await handle_mcp_request(request)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
