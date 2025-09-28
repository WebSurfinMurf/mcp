"""
MCP Filesystem Server
Provides file system operations via SSE MCP endpoint
"""
import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import aiofiles

app = FastAPI(title="MCP Filesystem Server", version="1.0.0")

# Configuration
WORKSPACE_PATH = os.getenv("WORKSPACE_PATH", "/workspace")
TEMP_PATH = os.getenv("TEMP_PATH", "/tmp")
MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "filesystem")

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
                    "tools": {},
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
    """SSE endpoint for MCP communication"""
    
    # Use a queue to manage incoming data from the client
    request_queue = asyncio.Queue()

    async def read_requests():
        """Task to read incoming data from the client and put it on the queue."""
        async for chunk in request.stream():
            try:
                # Assuming one JSON object per chunk for simplicity
                # A more robust implementation might handle chunk buffering
                data = chunk.decode('utf-8')
                if data:
                    await request_queue.put(data)
            except asyncio.CancelledError:
                break
            except Exception:
                # Handle potential decoding errors, etc.
                break

    async def event_stream():
        """Generate SSE events by processing requests from the queue."""
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connection', 'server': MCP_SERVER_NAME})}\n\n"

        # Start the task that reads from the client
        read_task = asyncio.create_task(read_requests())

        try:
            while True:
                # Wait for a request from the client
                try:
                    raw_request = await asyncio.wait_for(request_queue.get(), timeout=300) # 5 min timeout
                    mcp_request_data = json.loads(raw_request)
                    mcp_request = MCPRequest(**mcp_request_data)
                    
                    # Process the request using the existing handler
                    mcp_response = await handle_mcp_request(mcp_request)
                    
                    # Send the response back to the client
                    yield f"data: {mcp_response.json()}\n\n"

                except asyncio.TimeoutError:
                    # If no request for a while, send a ping
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                except json.JSONDecodeError:
                    error_resp = MCPResponse(error={"code": -32700, "message": "Parse error in request"})
                    yield f"data: {error_resp.json()}\n\n"

                if await request.is_disconnected():
                    break
        
        except asyncio.CancelledError:
            pass
        
        finally:
            # Clean up the reading task when the connection closes
            read_task.cancel()

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