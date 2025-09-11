"""
Base SSE server class for MCP services
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from core.models import ServiceInfo, HealthStatus, SSEEvent, EndpointCapabilities, ToolSchema
from core.protocol import MCPProtocolHandler
from core.utils import setup_logging, create_sse_event, get_service_uptime


class MCPSSEServer:
    """Base class for MCP SSE services"""
    
    def __init__(self, name: str, version: str = "1.0.0", port: int = 8000):
        self.name = name
        self.version = version
        self.port = port
        self.start_time = datetime.now()
        self.protocol_version = "2025-06-18"
        
        # Set up logging
        self.logger = setup_logging(f"mcp-{name}")
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title=f"MCP {name.title()} Service",
            version=version,
            description=f"Model Context Protocol service for {name}"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Initialize protocol handler
        self.protocol_handler = MCPProtocolHandler()
        
        # Set up routes
        self._setup_routes()
        
        # Exception handler
        self._setup_exception_handlers()
        
        self.logger.info(f"Initialized {name} MCP SSE server on port {port}")
    
    def register_tool(self, name: str, handler: Callable, input_schema: BaseModel, description: str, output_schema: Optional[BaseModel] = None):
        """Register a tool with the service (MCP 2025-06-18 with output schema support)"""
        # Convert Pydantic models to JSON schemas
        input_json_schema = input_schema.model_json_schema() if hasattr(input_schema, 'model_json_schema') else input_schema.schema()
        output_json_schema = None
        if output_schema:
            output_json_schema = output_schema.model_json_schema() if hasattr(output_schema, 'model_json_schema') else output_schema.schema()
        
        # Wrap handler to be async if it isn't already
        async def async_handler(**kwargs):
            if asyncio.iscoroutinefunction(handler):
                return await handler(**kwargs)
            else:
                return handler(**kwargs)
        
        self.protocol_handler.register_tool(name, async_handler, input_json_schema, description, output_json_schema)
        self.logger.info(f"Registered tool: {name} (MCP 2025-06-18)")
    
    def _setup_routes(self):
        """Set up FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return HealthStatus(
                status="healthy",
                service=self.name,
                version=self.version,
                uptime=get_service_uptime(self.start_time),
                tools_count=len(self.protocol_handler.tools)
            )
        
        @self.app.get("/info")
        async def service_info():
            """Service information endpoint"""
            return ServiceInfo(
                name=self.name,
                version=self.version,
                protocol_version=self.protocol_version,
                port=self.port,
                uptime=get_service_uptime(self.start_time),
                tools_count=len(self.protocol_handler.tools)
            )
        
        @self.app.api_route("/mcp", methods=["GET", "POST", "HEAD"])
        async def mcp_endpoint(request: Request):
            """MCP HTTP Transport endpoint (2025-03-26 specification)"""
            
            # Handle different HTTP methods
            if request.method == "GET":
                # GET request - return server info and capabilities
                tools = []
                for name, tool_data in self.protocol_handler.tools.items():
                    tool_def = {
                        "name": name,
                        "description": tool_data["description"],
                        "inputSchema": tool_data["input_schema"]
                    }
                    if tool_data.get("output_schema"):
                        tool_def["outputSchema"] = tool_data["output_schema"]
                    tools.append(tool_def)
                
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {
                            "tools": {
                                "listChanged": True
                            }
                        },
                        "serverInfo": {
                            "name": self.name,
                            "version": self.version
                        },
                        "tools": tools
                    }
                }
            
            elif request.method == "POST":
                # POST request - handle JSON-RPC messages
                try:
                    request_data = await request.json()
                    self.logger.info(f"POST request received: {request_data}")
                    
                    # Handle empty requests or requests without method field
                    if not request_data or request_data.get("method") is None:
                        self.logger.info("Empty or invalid POST request, returning capabilities")
                        # Return the same as GET request for compatibility
                        tools = []
                        for name, tool_data in self.protocol_handler.tools.items():
                            tool_def = {
                                "name": name,
                                "description": tool_data["description"],
                                "inputSchema": tool_data["input_schema"]
                            }
                            if tool_data.get("output_schema"):
                                tool_def["outputSchema"] = tool_data["output_schema"]
                            tools.append(tool_def)
                        
                        return {
                            "jsonrpc": "2.0",
                            "result": {
                                "protocolVersion": "2025-03-26",
                                "capabilities": {
                                    "tools": {
                                        "listChanged": True
                                    }
                                },
                                "serverInfo": {
                                    "name": self.name,
                                    "version": self.version
                                },
                                "tools": tools
                            }
                        }
                    
                    # Handle initialize request
                    if request_data.get("method") == "initialize":
                        return {
                            "jsonrpc": "2.0",
                            "id": request_data.get("id"),
                            "result": {
                                "protocolVersion": "2025-03-26",
                                "capabilities": {
                                    "tools": {
                                        "listChanged": True
                                    }
                                },
                                "serverInfo": {
                                    "name": self.name,
                                    "version": self.version
                                }
                            }
                        }
                    
                    # Handle tools/list request
                    elif request_data.get("method") == "tools/list":
                        tools = []
                        for name, tool_data in self.protocol_handler.tools.items():
                            tool_def = {
                                "name": name,
                                "description": tool_data["description"],
                                "inputSchema": tool_data["input_schema"]
                            }
                            if tool_data.get("output_schema"):
                                tool_def["outputSchema"] = tool_data["output_schema"]
                            tools.append(tool_def)
                        
                        return {
                            "jsonrpc": "2.0",
                            "id": request_data.get("id"),
                            "result": {
                                "tools": tools
                            }
                        }
                    
                    # Handle tools/call request
                    elif request_data.get("method") == "tools/call":
                        params = request_data.get("params", {})
                        tool_name = params.get("name")
                        arguments = params.get("arguments", {})
                        
                        if not tool_name or tool_name not in self.protocol_handler.tools:
                            return {
                                "jsonrpc": "2.0",
                                "id": request_data.get("id"),
                                "error": {
                                    "code": -32601,
                                    "message": f"Tool '{tool_name}' not found"
                                }
                            }
                        
                        # Execute tool
                        try:
                            tool_handler = self.protocol_handler.tools[tool_name]["handler"]
                            input_schema = self.protocol_handler.tools[tool_name]["input_schema"]
                            
                            if input_schema and hasattr(input_schema, '__call__'):
                                validated_input = input_schema(**arguments)
                                result = await tool_handler(validated_input)
                            else:
                                result = await tool_handler(**arguments)
                            
                            # Format result
                            if hasattr(result, 'dict'):
                                result_dict = result.dict()
                            elif hasattr(result, 'model_dump'):
                                result_dict = result.model_dump()
                            else:
                                result_dict = result
                            
                            return {
                                "jsonrpc": "2.0",
                                "id": request_data.get("id"),
                                "result": {
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": json.dumps(result_dict, indent=2)
                                        }
                                    ]
                                }
                            }
                        
                        except Exception as e:
                            return {
                                "jsonrpc": "2.0",
                                "id": request_data.get("id"),
                                "error": {
                                    "code": -32603,
                                    "message": f"Tool execution error: {str(e)}"
                                }
                            }
                    
                    # Handle other JSON-RPC requests
                    else:
                        return await self.protocol_handler.handle_request(request_data)
                        
                except Exception as e:
                    self.logger.error(f"Error processing POST request: {e}")
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": f"Parse error: {str(e)}"
                        }
                    }
            
            else:
                # HEAD request - just return success
                return {"status": "ok"}
        
        @self.app.get("/tools")
        async def list_tools():
            """List available tools"""
            return {"tools": self.protocol_handler.get_tool_list()}
        
        @self.app.api_route("/", methods=["GET", "POST", "HEAD"])
        async def root_endpoint(request: Request):
            """Root MCP endpoint as fallback"""
            tools = []
            for name, tool_data in self.protocol_handler.tools.items():
                tool_def = {
                    "name": name,
                    "description": tool_data["description"],
                    "inputSchema": tool_data["input_schema"]
                }
                if tool_data.get("output_schema"):
                    tool_def["outputSchema"] = tool_data["output_schema"]
                tools.append(tool_def)
            
            return {
                "jsonrpc": "2.0",
                "result": {
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": self.name,
                        "version": self.version
                    },
                    "tools": tools
                }
            }
        
        @self.app.post("/tools/call")
        async def call_tool(request_data: dict):
            """Direct tool calling endpoint for LiteLLM compatibility"""
            try:
                tool_name = request_data.get("name")
                arguments = request_data.get("arguments", {})
                
                if not tool_name:
                    return {
                        "error": "Missing 'name' parameter",
                        "code": -32602
                    }
                
                if tool_name not in self.protocol_handler.tools:
                    return {
                        "error": f"Tool '{tool_name}' not found",
                        "code": -32601
                    }
                
                # Call the tool directly
                tool_handler = self.protocol_handler.tools[tool_name]["handler"]
                input_schema = self.protocol_handler.tools[tool_name]["input_schema"]
                
                # Validate input
                try:
                    if input_schema and hasattr(input_schema, '__call__'):
                        # input_schema is a Pydantic model class
                        validated_input = input_schema(**arguments)
                        result = await tool_handler(validated_input)
                    else:
                        # Direct call without validation
                        result = await tool_handler(**arguments)
                except Exception as e:
                    return {
                        "error": f"Input validation error: {str(e)}",
                        "code": -32602
                    }
                
                # Format result for MCP compatibility
                if hasattr(result, 'dict'):
                    result_dict = result.dict()
                elif hasattr(result, 'model_dump'):
                    result_dict = result.model_dump()
                else:
                    result_dict = result
                
                return {
                    "content": [
                        {
                            "type": "text", 
                            "text": json.dumps(result_dict, indent=2)
                        }
                    ]
                }
                
            except Exception as e:
                self.logger.error(f"Tool call error: {e}")
                return {
                    "error": f"Tool execution error: {str(e)}",
                    "code": -32603
                }
        
        @self.app.post("/rpc")
        async def rpc_endpoint(request_data: dict):
            """JSON-RPC endpoint for synchronous tool execution"""
            try:
                response = await self.protocol_handler.handle_request(request_data)
                return response
            except Exception as e:
                self.logger.error(f"RPC error: {e}")
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    },
                    "id": request_data.get("id")
                }
        
        @self.app.get("/sse")
        async def sse_stream(request: Request):
            """Server-Sent Events stream for MCP communication"""
            return StreamingResponse(
                self._sse_generator(request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control",
                }
            )
    
    def _setup_exception_handlers(self):
        """Set up global exception handlers"""
        
        @self.app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            self.logger.error(f"Unhandled exception: {exc}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": str(exc)
                }
            )
    
    async def _sse_generator(self, request: Request):
        """Generate SSE events for client connections"""
        try:
            self.logger.info("New SSE connection established")
            
            # Send initial connection event
            connection_event = create_sse_event(
                "connection",
                {
                    "service": self.name,
                    "version": self.version,
                    "protocol_version": self.protocol_version,
                    "timestamp": datetime.now().isoformat()
                }
            )
            yield connection_event
            
            # Send capabilities event
            # Create tool schemas with MCP 2025-06-18 output schema support
            tool_schemas = []
            for name, tool_data in self.protocol_handler.tools.items():
                schema = ToolSchema(
                    name=name,
                    description=tool_data["description"],
                    inputSchema=tool_data["input_schema"]
                )
                if tool_data.get("output_schema"):
                    schema.outputSchema = tool_data["output_schema"]
                tool_schemas.append(schema)
            
            capabilities = EndpointCapabilities(endpoints=tool_schemas)
            
            capabilities_event = create_sse_event(
                "endpoint",
                capabilities.dict()
            )
            yield capabilities_event
            
            # Keep connection alive with periodic pings
            last_ping = time.time()
            ping_interval = 30  # 30 seconds
            
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    self.logger.info("SSE client disconnected")
                    break
                
                # Send ping if needed
                current_time = time.time()
                if current_time - last_ping >= ping_interval:
                    ping_event = create_sse_event(
                        "ping",
                        {
                            "timestamp": datetime.now().isoformat(),
                            "uptime": get_service_uptime(self.start_time)
                        }
                    )
                    yield ping_event
                    last_ping = current_time
                
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"SSE stream error: {e}")
            error_event = create_sse_event(
                "error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
            yield error_event
    
    def get_service_info(self) -> dict:
        """Get service information"""
        return ServiceInfo(
            name=self.name,
            version=self.version,
            protocol_version=self.protocol_version,
            port=self.port,
            uptime=get_service_uptime(self.start_time),
            tools_count=len(self.protocol_handler.tools)
        ).dict()
    
    def get_endpoints(self) -> dict:
        """Generate the endpoint capabilities structure (MCP 2025-06-18)"""
        tool_list = []
        for name, tool_data in self.protocol_handler.tools.items():
            tool_def = {
                "name": name,
                "description": tool_data["description"],
                "inputSchema": tool_data["input_schema"]
            }
            # Add output schema if available (MCP 2025-06-18 feature)
            if tool_data.get("output_schema"):
                tool_def["outputSchema"] = tool_data["output_schema"]
            tool_list.append(tool_def)
        return {"endpoints": tool_list}
    
    async def run_async(self):
        """Run the server asynchronously"""
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info",
            access_log=False
        )
        server = uvicorn.Server(config)
        
        try:
            self.logger.info(f"Starting {self.name} MCP SSE server on port {self.port}")
            await server.serve()
        except KeyboardInterrupt:
            self.logger.info(f"Shutting down {self.name} MCP SSE server")
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            raise
    
    def run(self):
        """Start the SSE server (synchronous)"""
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            self.logger.info("Server stopped by user")
        except Exception as e:
            self.logger.error(f"Server failed to start: {e}")
            raise