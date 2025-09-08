"""
Base MCP Service Class with Security, Validation, and Logging
Provides dual-mode (stdio/SSE) operation for all MCP services
"""

import json
import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from pydantic import BaseModel, ValidationError
from datetime import datetime
import configparser

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]  # Log to stderr to avoid stdio interference
)

class MCPService:
    """Base class for all MCP services with security and validation"""
    
    def __init__(self, name: str, version: str, config_path: Optional[str] = None):
        self.name = name
        self.version = version
        self.tools = {}
        self.config = self._load_config(config_path)
        self.read_only = self.config.get('security', {}).get('read_only', False)
        self.allowed_paths = self._init_allowed_paths()
        
        # Initialize structured logging for this service
        self.logger = logging.getLogger(self.name)
        self.logger.info(f"Initializing {self.name} service version {self.version}")
        
        # Initialize state
        self.initialized = False
        self.client_info = None
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from INI file"""
        if not config_path:
            config_path = f"services/config/{self.name}.ini"
        
        config = {}
        if os.path.exists(config_path):
            parser = configparser.ConfigParser()
            parser.read(config_path)
            
            # Convert ConfigParser to dict
            for section in parser.sections():
                config[section] = {}
                for key, value in parser.items(section):
                    # Try to parse as JSON for complex types
                    try:
                        config[section][key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        # Keep as string if not JSON
                        config[section][key] = value
        
        return config
    
    def _init_allowed_paths(self) -> List[Path]:
        """Initialize and validate allowed paths from config"""
        paths = self.config.get('security', {}).get('allowed_paths', [])
        if isinstance(paths, str):
            paths = json.loads(paths)
        return [Path(p).resolve() for p in paths if p]
    
    def validate_path(self, path: str) -> bool:
        """Validate path against allowlist with canonicalization"""
        if not self.allowed_paths:
            return True  # No restrictions if no allowed paths configured
        
        target = Path(path).resolve()
        return any(target.is_relative_to(allowed) for allowed in self.allowed_paths)
    
    def wrap_json_rpc_response(self, result: Any, request_id: Optional[int] = None) -> Dict:
        """Wrap result in JSON-RPC 2.0 response format"""
        response = {
            "jsonrpc": "2.0",
            "result": result
        }
        if request_id is not None:
            response["id"] = request_id
        return response
    
    def wrap_json_rpc_error(self, code: int, message: str, request_id: Optional[int] = None, data: Any = None) -> Dict:
        """Wrap error in JSON-RPC 2.0 error format"""
        error = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            }
        }
        if request_id is not None:
            error["id"] = request_id
        if data:
            error["error"]["data"] = data
        return error
    
    def register_tool(self, name: str, handler: Callable, schema: type[BaseModel], 
                      write_operation: bool = False, description: str = ""):
        """Register a tool with security metadata"""
        self.tools[name] = {
            "handler": handler,
            "schema": schema,
            "write_operation": write_operation,
            "description": description
        }
        self.logger.debug(f"Registered tool: {name} (write={write_operation})")
    
    def process_tool_call(self, tool_name: str, arguments: Dict, request_id: Optional[int] = None) -> Dict:
        """Process tool call with security checks and Pydantic validation"""
        self.logger.info(f"Processing tool call: {tool_name} (id={request_id})")
        
        # Check if tool exists
        if tool_name not in self.tools:
            self.logger.warning(f"Tool not found: {tool_name}")
            return self.wrap_json_rpc_error(-32601, f"Method not found: {tool_name}", request_id)
        
        tool = self.tools[tool_name]
        
        # Check read-only mode
        if self.read_only and tool["write_operation"]:
            self.logger.warning(f"Write operation '{tool_name}' blocked in read-only mode")
            return self.wrap_json_rpc_error(-32600, "Operation not permitted in read-only mode", request_id)
        
        # Validate parameters with Pydantic
        try:
            param_model = tool["schema"]
            validated_params = param_model(**arguments)  # Automatic validation!
            self.logger.debug(f"Parameters validated for '{tool_name}'")
        except ValidationError as e:
            self.logger.error(f"Parameter validation failed for '{tool_name}': {e}")
            return self.wrap_json_rpc_error(-32602, "Invalid params", request_id, data=e.errors())
        
        try:
            result = tool["handler"](validated_params)
            self.logger.info(f"Tool call '{tool_name}' completed successfully")
            return self.wrap_json_rpc_response(result, request_id)
        except Exception as e:
            self.logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
            return self.wrap_json_rpc_error(-32603, str(e), request_id)
    
    def handle_initialize(self, params: Dict, request_id: Optional[int] = None) -> Dict:
        """Handle MCP initialize request"""
        self.client_info = params.get("clientInfo", {})
        self.initialized = True
        
        # Build capabilities based on registered tools
        capabilities = {}
        if self.tools:
            capabilities["tools"] = {"listChanged": False}
        
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": capabilities,
            "serverInfo": {
                "name": self.name,
                "version": self.version
            }
        }
        
        self.logger.info(f"Initialized with client: {self.client_info.get('name', 'unknown')}")
        return self.wrap_json_rpc_response(result, request_id)
    
    def handle_tools_list(self, request_id: Optional[int] = None) -> Dict:
        """Handle tools/list request"""
        tools = []
        for name, tool_info in self.tools.items():
            # Get schema from Pydantic model
            schema_dict = tool_info["schema"].model_json_schema()
            
            # Remove title from schema if present
            schema_dict.pop("title", None)
            
            tools.append({
                "name": name,
                "description": tool_info.get("description", f"{name} tool"),
                "inputSchema": {
                    "type": "object",
                    "properties": schema_dict.get("properties", {}),
                    "required": schema_dict.get("required", [])
                }
            })
        
        return self.wrap_json_rpc_response({"tools": tools}, request_id)
    
    def handle_tools_call(self, params: Dict, request_id: Optional[int] = None) -> Dict:
        """Handle tools/call request"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        result = self.process_tool_call(tool_name, arguments, request_id)
        
        # If the result is already a JSON-RPC response, return it
        if "jsonrpc" in result:
            return result
        
        # Otherwise wrap it
        return self.wrap_json_rpc_response({"content": [{"type": "text", "text": json.dumps(result)}]}, request_id)
    
    def process_json_rpc_request(self, request: Dict) -> Dict:
        """Process a single JSON-RPC request"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        self.logger.debug(f"Processing request: {method}")
        
        # Route to appropriate handler
        if method == "initialize":
            return self.handle_initialize(params, request_id)
        elif method == "tools/list":
            return self.handle_tools_list(request_id)
        elif method == "tools/call":
            return self.handle_tools_call(params, request_id)
        else:
            return self.wrap_json_rpc_error(-32601, f"Method not found: {method}", request_id)
    
    def run_stdio_mode(self):
        """Run service in stdio mode for Claude Code"""
        self.logger.info(f"Starting {self.name} in stdio mode")
        
        # Read from stdin, write to stdout
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
                response = self.process_json_rpc_request(request)
                
                # Write response to stdout
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON received: {e}")
                error_response = self.wrap_json_rpc_error(-32700, "Parse error")
                print(json.dumps(error_response), flush=True)
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}", exc_info=True)
                error_response = self.wrap_json_rpc_error(-32603, "Internal error")
                print(json.dumps(error_response), flush=True)
    
    async def run_sse_mode(self):
        """Run service in SSE mode using FastAPI for concurrency"""
        from fastapi import FastAPI, Request
        from fastapi.responses import StreamingResponse, JSONResponse
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn
        
        app = FastAPI(title=f"{self.name} MCP Service")
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @app.get("/health")
        async def health():
            """Health check endpoint"""
            return {"status": "healthy", "service": self.name, "version": self.version}
        
        @app.get("/sse")
        async def sse_endpoint():
            """SSE endpoint for streaming events"""
            async def event_generator():
                """Generate SSE events"""
                # Send initial connection event
                event = {
                    "event": "connection",
                    "data": {
                        "service": self.name,
                        "version": self.version,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"
                
                # Keep connection alive with periodic heartbeats
                while True:
                    await asyncio.sleep(30)
                    heartbeat = {
                        "event": "heartbeat",
                        "data": {"timestamp": datetime.now().isoformat()}
                    }
                    yield f"event: {heartbeat['event']}\ndata: {json.dumps(heartbeat['data'])}\n\n"
            
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        
        @app.post("/rpc")
        async def json_rpc_endpoint(request: Request):
            """JSON-RPC endpoint for tool execution"""
            try:
                body = await request.json()
                response = self.process_json_rpc_request(body)
                return JSONResponse(content=response)
            except Exception as e:
                self.logger.error(f"Error processing request: {e}", exc_info=True)
                return JSONResponse(
                    content=self.wrap_json_rpc_error(-32603, str(e)),
                    status_code=500
                )
        
        @app.get("/tools")
        async def list_tools():
            """List available tools"""
            response = self.handle_tools_list()
            return response.get("result", {})
        
        # Run the FastAPI server
        host = self.config.get("sse", {}).get("host", "0.0.0.0")
        port = int(self.config.get("sse", {}).get("port", 8000))
        
        self.logger.info(f"Starting SSE server on {host}:{port}")
        await uvicorn.run(app, host=host, port=port)
    
    def run(self, mode: str = "stdio"):
        """Run the service in specified mode"""
        if mode == "stdio":
            self.run_stdio_mode()
        elif mode == "sse":
            asyncio.run(self.run_sse_mode())
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'stdio' or 'sse'")