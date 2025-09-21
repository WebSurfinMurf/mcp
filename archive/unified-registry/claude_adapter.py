#!/usr/bin/env python3
"""
Claude Code MCP Adapter
Provides unified MCP tools to Claude Code via stdio JSON-RPC protocol
"""

import sys
import json
import subprocess
from typing import Dict, Any, List, Optional, Tuple
import logging
from tool_definitions import TOOL_DEFINITIONS, get_all_tools, find_tool

# Configure logging to stderr so it doesn't interfere with stdio
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

class ClaudeMCPAdapter:
    """MCP server adapter for Claude Code"""
    
    def __init__(self):
        self.initialized = False
        self.request_id = 0
        
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
                    "name": "unified-mcp-adapter",
                    "version": "1.0.0"
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
    
    def execute_docker_tool(self, docker_command: List[str], tool_name: str, 
                          arguments: Dict[str, Any], env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Execute a tool via Docker or process command"""
        # Build JSON-RPC requests
        requests = [
            {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "claude-adapter", "version": "1.0.0"}
                },
                "id": 1
            },
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                },
                "id": 2
            }
        ]
        
        input_data = "\n".join(json.dumps(r) for r in requests)
        
        try:
            # Prepare environment
            import os
            run_env = os.environ.copy() if env else None
            if env and run_env:
                run_env.update(env)
            
            # Execute command (Docker or direct process)
            result = subprocess.run(
                docker_command,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=30,
                env=run_env
            )
            
            # Parse output - look for the tool response
            lines = result.stdout.strip().split('\n')
            for line in reversed(lines):  # Check from end
                try:
                    response = json.loads(line)
                    if response.get("id") == 2:  # Tool response
                        if "result" in response:
                            return {"success": True, "result": response["result"]}
                        elif "error" in response:
                            return {"success": False, "error": response["error"]}
                except json.JSONDecodeError:
                    continue
            
            # If no valid response found
            return {"success": False, "error": {"message": "No valid response from tool"}}
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": {"message": "Tool execution timeout"}}
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return {"success": False, "error": {"message": str(e)}}
    
    def handle_tools_call(self, request_id: Any, params: Dict[str, Any]):
        """Handle tools/call request"""
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
        
        # Build command and environment based on service
        docker_command, env = self.build_command(service_name, service_def)
        
        # Execute the tool
        result = self.execute_docker_tool(
            docker_command,
            tool_def["mcp_name"],
            arguments,
            env
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
    
    def build_command(self, service_name: str, service_def: Dict[str, Any]) -> Tuple[List[str], Optional[Dict[str, str]]]:
        """Build command and environment for a service"""
        
        # Check if it has docker_command (Docker-based service)
        if "docker_command" in service_def:
            # Services that use Docker via wrapper scripts
            return service_def["docker_command"], None
            
        # Check if it has command (direct process execution)
        elif "command" in service_def:
            # Services that run directly (Node.js, npx, etc.)
            command = service_def["command"]
            env = service_def.get("env", None)
            
            # Special handling for GitHub MCP - need actual token
            if service_name == "github" and env:
                # Try to load GitHub token from secrets
                try:
                    import os
                    if os.path.exists("/home/administrator/secrets/github.env"):
                        with open("/home/administrator/secrets/github.env") as f:
                            for line in f:
                                if line.startswith("GITHUB_PERSONAL_ACCESS_TOKEN="):
                                    token = line.split("=", 1)[1].strip()
                                    env["GITHUB_PERSONAL_ACCESS_TOKEN"] = token
                                    break
                except Exception as e:
                    logger.warning(f"Could not load GitHub token: {e}")
            
            return command, env
            
        # Fallback for special cases
        elif service_name == "filesystem":
            return [
                "docker", "run", "--rm", "-i",
                "-v", "/home/administrator:/workspace:rw",
                "mcp/filesystem", "/workspace"
            ], None
        elif service_name == "postgres":
            return [
                "docker", "run", "--rm", "-i",
                "--network", "postgres-net",
                "-e", "DATABASE_URI=postgresql://admin:Pass123qp@postgres:5432/postgres",
                "crystaldba/postgres-mcp"
            ], None
        else:
            # Unknown service type
            logger.error(f"No command configuration for service: {service_name}")
            return [], None
    
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
        logger.info("Starting Claude MCP Adapter stdio loop")
        
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
                    # Can't send error without request ID
                    continue
                except Exception as e:
                    logger.error(f"Request handling error: {e}")
                    # Try to send error if we have request ID
                    if 'request' in locals() and 'id' in request:
                        self.send_error(request['id'], -32603, str(e))
                        
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down")
        except Exception as e:
            logger.error(f"Fatal error in stdio loop: {e}")
        finally:
            logger.info("Claude MCP Adapter shutting down")

def main():
    """Main entry point"""
    adapter = ClaudeMCPAdapter()
    adapter.run_stdio_loop()

if __name__ == "__main__":
    main()