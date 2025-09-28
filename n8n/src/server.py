"""
MCP n8n Server
Provides workflow automation operations via MCP endpoint
"""
import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Union
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import aiohttp
import logging

app = FastAPI(title="MCP n8n Server", version="1.0.0")

# Configuration
MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "n8n")
N8N_URL = os.getenv("N8N_URL", "http://n8n:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
TEMP_PATH = os.getenv("TEMP_PATH", "/tmp")

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

class N8nTools:
    """MCP tool implementations for n8n operations"""

    @staticmethod
    async def get_workflows() -> Dict[str, Any]:
        """List all workflows"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-N8N-API-KEY": N8N_API_KEY}
                async with session.get(f"{N8N_URL}/api/v1/workflows", headers=headers) as response:
                    if response.status == 200:
                        workflows = await response.json()
                        workflow_list = []
                        for workflow in workflows.get('data', []):
                            workflow_list.append({
                                'id': workflow.get('id'),
                                'name': workflow.get('name'),
                                'active': workflow.get('active'),
                                'createdAt': workflow.get('createdAt'),
                                'updatedAt': workflow.get('updatedAt'),
                                'nodes': len(workflow.get('nodes', []))
                            })

                        return {
                            "workflows": workflow_list,
                            "count": len(workflow_list),
                            "success": True
                        }
                    else:
                        return {"error": f"API request failed: {response.status}", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def get_workflow_details(workflow_id: str) -> Dict[str, Any]:
        """Get details of a specific workflow"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-N8N-API-KEY": N8N_API_KEY}
                async with session.get(f"{N8N_URL}/api/v1/workflows/{workflow_id}", headers=headers) as response:
                    if response.status == 200:
                        workflow = await response.json()
                        return {
                            "workflow": workflow,
                            "success": True
                        }
                    else:
                        return {"error": f"API request failed: {response.status}", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def execute_workflow(workflow_id: str, data: Dict = None) -> Dict[str, Any]:
        """Execute a workflow"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-N8N-API-KEY": N8N_API_KEY, "Content-Type": "application/json"}
                payload = data or {}
                async with session.post(f"{N8N_URL}/api/v1/workflows/{workflow_id}/execute",
                                      headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "execution": result,
                            "success": True
                        }
                    else:
                        return {"error": f"API request failed: {response.status}", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def get_executions(workflow_id: str = None, limit: int = 10) -> Dict[str, Any]:
        """Get workflow executions"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-N8N-API-KEY": N8N_API_KEY}
                params = {"limit": limit}
                if workflow_id:
                    params["workflowId"] = workflow_id

                async with session.get(f"{N8N_URL}/api/v1/executions",
                                     headers=headers, params=params) as response:
                    if response.status == 200:
                        executions = await response.json()
                        execution_list = []
                        for execution in executions.get('data', []):
                            execution_list.append({
                                'id': execution.get('id'),
                                'workflowId': execution.get('workflowId'),
                                'mode': execution.get('mode'),
                                'finished': execution.get('finished'),
                                'status': execution.get('status'),
                                'startedAt': execution.get('startedAt'),
                                'stoppedAt': execution.get('stoppedAt')
                            })

                        return {
                            "executions": execution_list,
                            "count": len(execution_list),
                            "success": True
                        }
                    else:
                        return {"error": f"API request failed: {response.status}", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def get_credentials() -> Dict[str, Any]:
        """List available credentials"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-N8N-API-KEY": N8N_API_KEY}
                async with session.get(f"{N8N_URL}/api/v1/credentials", headers=headers) as response:
                    if response.status == 200:
                        credentials = await response.json()
                        cred_list = []
                        for cred in credentials.get('data', []):
                            cred_list.append({
                                'id': cred.get('id'),
                                'name': cred.get('name'),
                                'type': cred.get('type'),
                                'createdAt': cred.get('createdAt'),
                                'updatedAt': cred.get('updatedAt')
                            })

                        return {
                            "credentials": cred_list,
                            "count": len(cred_list),
                            "success": True
                        }
                    else:
                        return {"error": f"API request failed: {response.status}", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def activate_workflow(workflow_id: str, active: bool = True) -> Dict[str, Any]:
        """Activate or deactivate a workflow"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-N8N-API-KEY": N8N_API_KEY, "Content-Type": "application/json"}
                payload = {"active": active}
                async with session.patch(f"{N8N_URL}/api/v1/workflows/{workflow_id}",
                                       headers=headers, json=payload) as response:
                    if response.status == 200:
                        workflow = await response.json()
                        return {
                            "workflow": workflow,
                            "action": "activated" if active else "deactivated",
                            "success": True
                        }
                    else:
                        return {"error": f"API request failed: {response.status}", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

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
                "name": "get_workflows",
                "description": "List all n8n workflows",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_workflow_details",
                "description": "Get details of a specific workflow",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "string", "description": "Workflow ID"}
                    },
                    "required": ["workflow_id"]
                }
            },
            {
                "name": "execute_workflow",
                "description": "Execute a workflow",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "string", "description": "Workflow ID"},
                        "data": {"type": "object", "description": "Input data for workflow", "default": {}}
                    },
                    "required": ["workflow_id"]
                }
            },
            {
                "name": "get_executions",
                "description": "Get workflow executions",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "string", "description": "Filter by workflow ID (optional)"},
                        "limit": {"type": "integer", "description": "Number of executions to return", "default": 10}
                    }
                }
            },
            {
                "name": "get_credentials",
                "description": "List available credentials",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "activate_workflow",
                "description": "Activate or deactivate a workflow",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "string", "description": "Workflow ID"},
                        "active": {"type": "boolean", "description": "Whether to activate (true) or deactivate (false)", "default": True}
                    },
                    "required": ["workflow_id"]
                }
            }
        ]

        return MCPResponse(result={"tools": tools}, id=request.id)

    elif request.method == "tools/call":
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})

        if tool_name == "get_workflows":
            result = await N8nTools.get_workflows()
        elif tool_name == "get_workflow_details":
            result = await N8nTools.get_workflow_details(**arguments)
        elif tool_name == "execute_workflow":
            result = await N8nTools.execute_workflow(**arguments)
        elif tool_name == "get_executions":
            result = await N8nTools.get_executions(**arguments)
        elif tool_name == "get_credentials":
            result = await N8nTools.get_credentials()
        elif tool_name == "activate_workflow":
            result = await N8nTools.activate_workflow(**arguments)
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
    try:
        # Test n8n connection
        async with aiohttp.ClientSession() as session:
            headers = {"X-N8N-API-KEY": N8N_API_KEY}
            async with session.get(f"{N8N_URL}/api/v1/workflows", headers=headers) as response:
                n8n_status = "connected" if response.status == 200 else "disconnected"
    except Exception:
        n8n_status = "disconnected"

    return {
        "status": "healthy",
        "service": MCP_SERVER_NAME,
        "n8n_url": N8N_URL,
        "n8n_status": n8n_status
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