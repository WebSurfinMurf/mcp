"""
MCP OpenMemory Server
Provides mem0 (OpenMemory) operations via MCP endpoint
Translates MCP protocol to OpenMemory REST API calls
"""
import os
import json
import requests
from typing import Dict, Any, Optional, Union, List
from fastapi import FastAPI, Request
from pydantic import BaseModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP OpenMemory Server", version="1.0.0")

# Configuration
OPENMEMORY_API = os.getenv("OPENMEMORY_API", "http://openmemory-api:8765")
OPENMEMORY_USER = os.getenv("OPENMEMORY_USER", "administrator")
OPENMEMORY_APP = os.getenv("OPENMEMORY_APP", "claude-code")

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

# MCP Tool Definitions
TOOLS = [
    {
        "name": "add_memory",
        "description": "Add a new memory to OpenMemory. Use this to save important facts, lessons learned, gotchas, solutions, and user preferences. Memories are automatically categorized and made searchable.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The memory text to store. Should be a complete, standalone fact or lesson."
                },
                "category": {
                    "type": "string",
                    "description": "Category for the memory (e.g., 'gotcha', 'lesson', 'solution', 'decision', 'preference')",
                    "enum": ["gotcha", "lesson", "solution", "decision", "preference", "fact", "note"]
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional metadata (project, timestamp, etc.)",
                    "additionalProperties": True
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "search_memories",
        "description": "Search memories using semantic similarity. Finds relevant memories even if the exact words don't match. Returns the most relevant memories ranked by similarity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (natural language)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10)",
                    "default": 10
                },
                "category": {
                    "type": "string",
                    "description": "Filter by category (optional)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "list_memories",
        "description": "List all memories with optional filtering by category, date range, or search query. Returns paginated results.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by category (optional)"
                },
                "search_query": {
                    "type": "string",
                    "description": "Text search filter (optional)"
                },
                "page": {
                    "type": "integer",
                    "description": "Page number (default: 1)",
                    "default": 1
                },
                "size": {
                    "type": "integer",
                    "description": "Page size (default: 50, max: 100)",
                    "default": 50
                }
            }
        }
    },
    {
        "name": "delete_memory",
        "description": "Delete a specific memory by ID. Use with caution as this is permanent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "string",
                    "description": "The UUID of the memory to delete"
                }
            },
            "required": ["memory_id"]
        }
    }
]

def call_openmemory_api(method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
    """Call OpenMemory REST API"""
    url = f"{OPENMEMORY_API}{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, json=data, timeout=30)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"OpenMemory API error: {e}")
        raise

def handle_add_memory(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new memory"""
    text = arguments.get("text")
    category = arguments.get("category", "note")
    metadata = arguments.get("metadata", {})

    # Add category to metadata
    metadata["category"] = category

    # Create memory
    data = {
        "user_id": OPENMEMORY_USER,
        "text": text,
        "metadata": metadata,
        "app": OPENMEMORY_APP,
        "infer": True  # Let mem0 extract entities/facts
    }

    result = call_openmemory_api("POST", "/api/v1/memories/", data=data)
    return {
        "success": True,
        "memory_id": result.get("id"),
        "message": f"Memory added successfully with category '{category}'",
        "result": result
    }

def handle_search_memories(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Search memories semantically"""
    query = arguments.get("query")
    limit = arguments.get("limit", 10)
    category = arguments.get("category")

    # Build query parameters
    params = {
        "user_id": OPENMEMORY_USER,
        "search_query": query,
        "size": limit
    }

    if category:
        params["categories"] = category

    result = call_openmemory_api("GET", "/api/v1/memories/", params=params)

    return {
        "success": True,
        "count": len(result.get("items", [])),
        "memories": result.get("items", []),
        "total": result.get("total", 0)
    }

def handle_list_memories(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """List all memories with filtering"""
    params = {
        "user_id": OPENMEMORY_USER,
        "page": arguments.get("page", 1),
        "size": arguments.get("size", 50)
    }

    if arguments.get("category"):
        params["categories"] = arguments["category"]

    if arguments.get("search_query"):
        params["search_query"] = arguments["search_query"]

    result = call_openmemory_api("GET", "/api/v1/memories/", params=params)

    return {
        "success": True,
        "count": len(result.get("items", [])),
        "memories": result.get("items", []),
        "total": result.get("total", 0),
        "page": params["page"],
        "size": params["size"]
    }

def handle_delete_memory(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a memory by ID"""
    memory_id = arguments.get("memory_id")

    data = {
        "memory_ids": [memory_id]
    }

    result = call_openmemory_api("DELETE", "/api/v1/memories/", data=data)

    return {
        "success": True,
        "message": f"Memory {memory_id} deleted successfully",
        "result": result
    }

@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """Main MCP endpoint"""
    try:
        method = request.method
        params = request.params or {}

        # Handle MCP protocol methods
        if method == "initialize":
            return MCPResponse(
                id=request.id,
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "openmemory",
                        "version": "1.0.0"
                    }
                }
            )

        elif method == "tools/list":
            return MCPResponse(
                id=request.id,
                result={"tools": TOOLS}
            )

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            # Route to appropriate handler
            if tool_name == "add_memory":
                result = handle_add_memory(arguments)
            elif tool_name == "search_memories":
                result = handle_search_memories(arguments)
            elif tool_name == "list_memories":
                result = handle_list_memories(arguments)
            elif tool_name == "delete_memory":
                result = handle_delete_memory(arguments)
            else:
                return MCPResponse(
                    id=request.id,
                    error={
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                )

            return MCPResponse(
                id=request.id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            )

        else:
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32601,
                    "message": f"Unknown method: {method}"
                }
            )

    except Exception as e:
        logger.error(f"Error handling MCP request: {e}", exc_info=True)
        return MCPResponse(
            id=request.id,
            error={
                "code": -32603,
                "message": str(e)
            }
        )

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Test connection to OpenMemory API
        response = requests.get(f"{OPENMEMORY_API}/api/v1/config/", timeout=5)
        response.raise_for_status()

        return {
            "status": "healthy",
            "openmemory_api": OPENMEMORY_API,
            "user": OPENMEMORY_USER,
            "app": OPENMEMORY_APP
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
