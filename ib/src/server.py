"""
MCP IB (Interactive Brokers) Server
Provides market data and portfolio operations via MCP endpoint
"""
import os
import json
import asyncio
import subprocess
from typing import Dict, Any, Optional, Union
from fastapi import FastAPI, Request
from pydantic import BaseModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP IB Server", version="1.0.0")

# Configuration
MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "ib")
IB_HOST = os.getenv("IB_HOST", "mcp-ib-gateway")
IB_PORT = os.getenv("IB_PORT", "4002")
IB_CLIENT_ID = os.getenv("IB_CLIENT_ID", "1")

# IB MCP process
ib_process = None
ib_initialized = False

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

async def send_to_ib_mcp(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send request to IB MCP server via subprocess"""
    global ib_process, ib_initialized

    try:
        # Initialize process if needed
        if ib_process is None:
            logger.info(f"Starting IB MCP server: host={IB_HOST}, port={IB_PORT}")
            ib_process = await asyncio.create_subprocess_exec(
                "python3", "-m", "ib_mcp.server",
                "--host", IB_HOST,
                "--port", IB_PORT,
                "--client-id", IB_CLIENT_ID,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Send initialize message if first time
            if not ib_initialized:
                init_msg = {
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "mcp-ib-http", "version": "1.0.0"}
                    },
                    "id": "init"
                }
                ib_process.stdin.write(json.dumps(init_msg).encode() + b'\n')
                await ib_process.stdin.drain()

                # Read initialize response
                init_response = await asyncio.wait_for(
                    ib_process.stdout.readline(),
                    timeout=10.0
                )
                logger.info(f"IB MCP initialized: {init_response.decode().strip()}")

                # Send initialized notification
                initialized_notif = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {}
                }
                ib_process.stdin.write(json.dumps(initialized_notif).encode() + b'\n')
                await ib_process.stdin.drain()

                ib_initialized = True

        # If this is an initialize request, just return cached response
        if request_data.get("method") == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_data.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "experimental": {},
                        "prompts": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                        "tools": {"listChanged": True}
                    },
                    "serverInfo": {
                        "name": "IBKR MCP Server",
                        "version": "1.16.0"
                    },
                    "instructions": "Fetch portfolio and market data using IBKR TWS APIs."
                }
            }

        # Send actual request
        ib_process.stdin.write(json.dumps(request_data).encode() + b'\n')
        await ib_process.stdin.drain()

        # Read response
        response_line = await asyncio.wait_for(
            ib_process.stdout.readline(),
            timeout=30.0
        )

        if not response_line:
            raise Exception("IB MCP process closed")

        return json.loads(response_line.decode().strip())

    except asyncio.TimeoutError:
        logger.error("Timeout waiting for IB MCP response")
        # Reset process on timeout to allow retry
        if ib_process:
            try:
                ib_process.terminate()
                await ib_process.wait()
            except:
                pass
            ib_process = None
            ib_initialized = False
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": "Timeout waiting for IB response"},
            "id": request_data.get("id")
        }
    except Exception as e:
        logger.error(f"Error communicating with IB MCP: {e}")
        # Reset process on error
        if ib_process:
            try:
                ib_process.terminate()
                await ib_process.wait()
            except:
                pass
            ib_process = None
            ib_initialized = False

        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": request_data.get("id")
        }

@app.on_event("startup")
async def startup_event():
    """Initialize IB MCP connection on startup"""
    logger.info(f"Starting MCP IB Server - connecting to {IB_HOST}:{IB_PORT}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global ib_process
    if ib_process:
        logger.info("Shutting down IB MCP process")
        try:
            ib_process.terminate()
            await ib_process.wait()
        except:
            pass

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": MCP_SERVER_NAME,
        "ib_host": IB_HOST,
        "ib_port": IB_PORT,
        "ib_initialized": ib_initialized
    }

@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """HTTP POST endpoint for MCP requests"""
    request_dict = request.dict()
    response_dict = await send_to_ib_mcp(request_dict)
    return response_dict

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
