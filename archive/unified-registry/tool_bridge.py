"""
MCP Tool Bridge - Handles communication with MCP services
Can use either SSE proxy or direct Docker execution
"""

import json
import subprocess
import asyncio
import aiohttp
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MCPToolBridge:
    """Bridge for executing MCP tools via different transports"""
    
    def __init__(self, use_sse_proxy=False):
        """
        Initialize the bridge
        Args:
            use_sse_proxy: If True, use SSE proxy. If False, use direct Docker execution
        """
        self.use_sse_proxy = use_sse_proxy
        self.session = None
        
    async def __aenter__(self):
        if self.use_sse_proxy:
            self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def execute_tool_sse(self, endpoint: str, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool via SSE proxy endpoint"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        # Build JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": params
            },
            "id": 1
        }
        
        try:
            # Send to SSE endpoint
            async with self.session.post(
                endpoint.replace('/sse', '/rpc'),  # Convert SSE endpoint to RPC
                json=request,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "result" in result:
                        return {"success": True, "data": result["result"]}
                    elif "error" in result:
                        return {"success": False, "error": result["error"]}
                else:
                    return {"success": False, "error": f"HTTP {response.status}"}
                    
        except Exception as e:
            logger.error(f"SSE execution error: {e}")
            return {"success": False, "error": str(e)}
    
    def execute_tool_docker(self, docker_command: list, tool_name: str, params: Dict[str, Any], env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Execute a tool via direct Docker or process command"""
        # Build JSON-RPC request sequence
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "unified-mcp", "version": "1.0.0"}
            },
            "id": 1
        }
        
        tool_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": params
            },
            "id": 2
        }
        
        try:
            # Prepare input
            input_data = json.dumps(init_request) + "\n" + json.dumps(tool_request) + "\n"
            
            # Prepare environment variables
            run_env = None
            if env:
                import os
                run_env = os.environ.copy()
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
            
            if result.returncode != 0:
                return {"success": False, "error": f"Execution error: {result.stderr}"}
            
            # Parse output - look for the tool response
            lines = result.stdout.strip().split('\n')
            for line in reversed(lines):  # Check from end
                try:
                    response = json.loads(line)
                    if response.get("id") == 2:  # Tool response
                        if "result" in response:
                            return {"success": True, "data": response["result"]}
                        elif "error" in response:
                            return {"success": False, "error": response["error"]}
                except json.JSONDecodeError:
                    continue
                    
            return {"success": False, "error": "No valid response found"}
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Execution timeout"}
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_tool(self, service: str, endpoint: str, docker_command: list, 
                          tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool using the configured transport
        
        Args:
            service: Service name (e.g., "filesystem")
            endpoint: SSE endpoint URL
            docker_command: Docker command to run MCP server
            tool_name: Name of the tool to execute
            params: Parameters for the tool
            
        Returns:
            Dict with success status and data or error
        """
        if self.use_sse_proxy:
            return await self.execute_tool_sse(endpoint, tool_name, params)
        else:
            return self.execute_tool_docker(docker_command, tool_name, params)
    
    def list_tools_docker(self, docker_command: list) -> Dict[str, Any]:
        """List available tools via direct Docker command"""
        # Build JSON-RPC request sequence
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "unified-mcp", "version": "1.0.0"}
            },
            "id": 1
        }
        
        list_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }
        
        try:
            # Prepare input
            input_data = json.dumps(init_request) + "\n" + json.dumps(list_request) + "\n"
            
            # Execute Docker command
            result = subprocess.run(
                docker_command,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {"success": False, "error": f"Docker error: {result.stderr}"}
            
            # Parse output - look for the tools list response
            lines = result.stdout.strip().split('\n')
            for line in reversed(lines):
                try:
                    response = json.loads(line)
                    if response.get("id") == 2:  # Tools list response
                        if "result" in response:
                            return {"success": True, "tools": response["result"].get("tools", [])}
                        elif "error" in response:
                            return {"success": False, "error": response["error"]}
                except json.JSONDecodeError:
                    continue
                    
            return {"success": False, "error": "No valid response found"}
            
        except Exception as e:
            logger.error(f"Docker list tools error: {e}")
            return {"success": False, "error": str(e)}