#!/usr/bin/env python3
"""
Claude Code MCP Adapter - SSE Version
Uses SSE proxy for tool execution instead of direct Docker spawning
"""

import sys
import json
import logging
from typing import Dict, Any
from tool_definitions import TOOL_DEFINITIONS
from sse_client import DirectMCPClient

# Configure logging to stderr so it doesn't interfere with stdio
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

class ClaudeMCPAdapterSSE:
    """MCP server adapter for Claude Code using persistent subprocess connections"""
    
    def __init__(self):
        self.initialized = False
        self.mcp_client = DirectMCPClient()  # Use direct MCP client with persistent processes
        
    def send_response(self, response: Dict[str, Any]):
        """Send JSON-RPC response to stdout"""
        json_str = json.dumps(response)
        sys.stdout.write(json_str + "\n")
        sys.stdout.flush()
        logger.debug(f"Sent response: {json_str}")
    
    def send_error(self, request_id: Any, code: int, message: str, data: Any = None):
        """Send JSON-RPC error response"""
        error_response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        if data is not None:
            error_response["error"]["data"] = data
        self.send_response(error_response)
    
    def handle_initialize(self, request_id: Any, params: Dict[str, Any]):
        """Handle initialization request"""
        logger.info("Handling initialize request")
        
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "unified-mcp-adapter-sse",
                    "version": "2.0.0"
                }
            }
        }
        
        self.initialized = True
        self.send_response(response)
    
    def handle_tools_list(self, request_id: Any, params: Dict[str, Any]):
        """Handle tools/list request"""
        logger.info("Handling tools/list request")
        
        if not self.initialized:
            self.send_error(request_id, -32002, "Server not initialized")
            return
        
        # Get all tools from the registry
        tools = []
        for service_name, service_def in TOOL_DEFINITIONS.items():
            for tool in service_def["tools"]:
                tools.append({
                    "name": f"{service_name}_{tool['name']}",
                    "description": f"[{service_name.upper()}] {tool['description']}",
                    "inputSchema": tool["parameters_schema"]
                })
        
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools
            }
        }
        
        self.send_response(response)
    
    def handle_tools_call(self, request_id: Any, params: Dict[str, Any]):
        """Handle tools/call request using persistent MCP connections"""
        logger.info(f"Handling tools/call request: {params.get('name')}")
        
        if not self.initialized:
            self.send_error(request_id, -32002, "Server not initialized")
            return
        
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        # Parse service and tool name
        if "_" not in tool_name:
            self.send_error(request_id, -32602, f"Invalid tool name format: {tool_name}")
            return
        
        service_name, actual_tool_name = tool_name.split("_", 1)
        
        # Find the tool definition
        if service_name not in TOOL_DEFINITIONS:
            self.send_error(request_id, -32602, f"Unknown service: {service_name}")
            return
        
        service_def = TOOL_DEFINITIONS[service_name]
        tool_def = None
        for tool in service_def["tools"]:
            if tool["name"] == actual_tool_name:
                tool_def = tool
                break
        
        if not tool_def:
            self.send_error(request_id, -32602, f"Unknown tool: {actual_tool_name}")
            return
        
        # Build command for the service
        command = self.build_command(service_name, service_def)
        if not command:
            self.send_error(request_id, -32603, f"No command configured for service: {service_name}")
            return
        
        # Execute tool using persistent MCP client
        result = self.mcp_client.call_tool(
            service_name,
            command,
            tool_def["mcp_name"],
            arguments
        )
        
        if result["success"]:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result["result"]
            }
            self.send_response(response)
        else:
            error = result.get("error", {})
            self.send_error(
                request_id,
                error.get("code", -32603),
                error.get("message", "Tool execution failed"),
                error.get("data")
            )
    
    def build_command(self, service_name: str, service_def: Dict[str, Any]) -> list:
        """Build command for a service"""
        
        # For services that have Docker wrapper scripts
        if "docker_command" in service_def:
            return service_def["docker_command"]
        
        # For services that run directly (Node.js, npx, etc.)
        elif "command" in service_def:
            command = service_def["command"]
            
            # Special handling for GitHub - need to set environment
            if service_name == "github":
                # The command will be executed with proper environment by DirectMCPClient
                return command
            
            return command
        
        # Fallback for special cases based on service name
        elif service_name == "filesystem":
            return [
                "docker", "run", "--rm", "-i",
                "-v", "/home/administrator:/workspace:rw",
                "mcp/filesystem"
            ]
        elif service_name == "postgres":
            return [
                "docker", "run", "--rm", "-i",
                "--network", "postgres-net",
                "-e", "DATABASE_URI=postgresql://admin:Pass123qp@postgres:5432/postgres",
                "crystaldba/postgres-mcp"
            ]
        else:
            logger.error(f"No command configuration for service: {service_name}")
            return []
    
    def handle_request(self, request: Dict[str, Any]):
        """Handle a JSON-RPC request"""
        request_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})
        
        logger.info(f"Handling request: {method}")
        
        if method == "initialize":
            self.handle_initialize(request_id, params)
        elif method == "tools/list":
            self.handle_tools_list(request_id, params)
        elif method == "tools/call":
            self.handle_tools_call(request_id, params)
        else:
            self.send_error(request_id, -32601, f"Method not found: {method}")
    
    def run_stdio_loop(self):
        """Main JSON-RPC over stdio loop"""
        logger.info("Starting Claude MCP Adapter SSE stdio loop")
        
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    request = json.loads(line)
                    self.handle_request(request)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Request handling error: {e}")
                    if 'request' in locals() and 'id' in request:
                        self.send_error(request['id'], -32603, str(e))
                        
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down")
        except Exception as e:
            logger.error(f"Fatal error in stdio loop: {e}")
        finally:
            logger.info("Closing MCP connections")
            self.mcp_client.close()
            logger.info("Claude MCP Adapter SSE shutting down")

def main():
    """Main entry point"""
    adapter = ClaudeMCPAdapterSSE()
    adapter.run_stdio_loop()

if __name__ == "__main__":
    main()