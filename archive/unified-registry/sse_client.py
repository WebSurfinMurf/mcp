#!/usr/bin/env python3
"""
SSE Client for MCP Proxy Communication
Handles Server-Sent Events communication with MCP services via the SSE proxy
"""

import json
import logging
import time
from typing import Dict, Any, Optional
import requests
from threading import Lock

logger = logging.getLogger(__name__)

class SSEMCPClient:
    """Client for communicating with MCP services via SSE proxy"""
    
    def __init__(self, base_url: str = "http://localhost:8585"):
        self.base_url = base_url
        self.sessions = {}  # Service -> requests.Session mapping
        self.session_lock = Lock()
        self.initialized_services = set()
        
    def _get_session(self, service: str) -> requests.Session:
        """Get or create a session for a service"""
        with self.session_lock:
            if service not in self.sessions:
                self.sessions[service] = requests.Session()
                # Keep connection alive
                self.sessions[service].headers.update({
                    'Accept': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive'
                })
            return self.sessions[service]
    
    def _parse_sse_response(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse SSE response to extract JSON-RPC response"""
        lines = text.strip().split('\n')
        for line in lines:
            if line.startswith('data: '):
                try:
                    data = line[6:]  # Remove 'data: ' prefix
                    if data and data != '[DONE]':
                        return json.loads(data)
                except json.JSONDecodeError:
                    continue
        return None
    
    def _ensure_initialized(self, service: str) -> bool:
        """Ensure a service is initialized before use"""
        if service in self.initialized_services:
            return True
            
        try:
            # Send initialization request
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "unified-mcp-adapter", "version": "1.0.0"}
                },
                "id": f"init_{service}_{int(time.time())}"
            }
            
            # Send via SSE endpoint
            url = f"{self.base_url}/servers/{service}/sse"
            session = self._get_session(service)
            
            # Send as JSON-RPC over SSE
            response = session.post(
                url,
                json=init_request,
                timeout=5,
                stream=False
            )
            
            if response.status_code == 200:
                self.initialized_services.add(service)
                logger.info(f"Initialized service: {service}")
                return True
            else:
                logger.error(f"Failed to initialize {service}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing {service}: {e}")
            return False
    
    def call_tool(self, service: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on a specific MCP service via SSE proxy"""
        
        # Ensure service is initialized
        if not self._ensure_initialized(service):
            return {
                "success": False,
                "error": {"message": f"Failed to initialize service: {service}"}
            }
        
        try:
            # Build tool call request
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                },
                "id": f"tool_{int(time.time())}"
            }
            
            # Send to SSE endpoint
            url = f"{self.base_url}/servers/{service}/sse"
            session = self._get_session(service)
            
            # Send request and get response
            response = session.post(
                url,
                json=request,
                timeout=30,
                stream=True
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": {"message": f"HTTP {response.status_code}: {response.text}"}
                }
            
            # Read SSE stream for response
            result_data = None
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])
                            if data.get("id") == request["id"]:
                                result_data = data
                                break
                        except json.JSONDecodeError:
                            continue
            
            if result_data:
                if "result" in result_data:
                    return {"success": True, "result": result_data["result"]}
                elif "error" in result_data:
                    return {"success": False, "error": result_data["error"]}
            
            # Fallback: Try to parse the entire response
            parsed = self._parse_sse_response(response.text)
            if parsed:
                if "result" in parsed:
                    return {"success": True, "result": parsed["result"]}
                elif "error" in parsed:
                    return {"success": False, "error": parsed["error"]}
            
            return {
                "success": False,
                "error": {"message": "No valid response from SSE proxy"}
            }
            
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": {"message": "Request timeout"}
            }
        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on {service}: {e}")
            return {
                "success": False,
                "error": {"message": str(e)}
            }
    
    def close(self):
        """Close all sessions"""
        with self.session_lock:
            for session in self.sessions.values():
                session.close()
            self.sessions.clear()
            self.initialized_services.clear()

# Alternative approach using direct MCP communication via subprocess
class DirectMCPClient:
    """Direct MCP client that maintains persistent subprocess connections"""
    
    def __init__(self):
        self.processes = {}
        self.process_lock = Lock()
        
    def _get_or_create_process(self, service: str, command: list) -> Any:
        """Get or create a persistent subprocess for a service"""
        import subprocess
        
        with self.process_lock:
            if service not in self.processes:
                # Start persistent subprocess
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=0  # Unbuffered
                )
                
                # Send initialization
                init_request = json.dumps({
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "unified-mcp-adapter", "version": "1.0.0"}
                    },
                    "id": 1
                }) + "\n"
                
                process.stdin.write(init_request)
                process.stdin.flush()
                
                # Read initialization response
                response_line = process.stdout.readline()
                try:
                    response = json.loads(response_line)
                    if "result" in response:
                        logger.info(f"Initialized service {service}")
                        self.processes[service] = process
                except json.JSONDecodeError:
                    logger.error(f"Failed to initialize {service}")
                    process.terminate()
                    return None
                    
            return self.processes.get(service)
    
    def call_tool(self, service: str, command: list, tool_name: str, 
                  arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool using persistent subprocess"""
        
        process = self._get_or_create_process(service, command)
        if not process:
            return {
                "success": False,
                "error": {"message": f"Failed to initialize service: {service}"}
            }
        
        try:
            # Send tool request
            request = json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                },
                "id": int(time.time())
            }) + "\n"
            
            process.stdin.write(request)
            process.stdin.flush()
            
            # Read response
            response_line = process.stdout.readline()
            response = json.loads(response_line)
            
            if "result" in response:
                return {"success": True, "result": response["result"]}
            elif "error" in response:
                return {"success": False, "error": response["error"]}
            else:
                return {
                    "success": False,
                    "error": {"message": "Invalid response format"}
                }
                
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            # Remove failed process
            with self.process_lock:
                if service in self.processes:
                    self.processes[service].terminate()
                    del self.processes[service]
            return {
                "success": False,
                "error": {"message": str(e)}
            }
    
    def close(self):
        """Terminate all processes"""
        with self.process_lock:
            for process in self.processes.values():
                process.terminate()
            self.processes.clear()