#!/usr/bin/env python3
"""
Claude Code MCP Bridge
Bridges the centralized MCP server HTTP API to MCP stdio protocol for Claude Code integration
"""

import json
import sys
import requests
import traceback
import logging
import datetime
from typing import Dict, Any, List

# Set up logging to a file for debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/mcp-bridge.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

MCP_SERVER_URL = "http://mcp.linuxserver.lan:8001"

class MCPBridge:
    def __init__(self):
        self.tools_cache = None

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from MCP server"""
        logger.debug(f"Getting tools from {MCP_SERVER_URL}/tools")
        if self.tools_cache is None:
            try:
                response = requests.get(f"{MCP_SERVER_URL}/tools", timeout=10)
                response.raise_for_status()
                data = response.json()
                self.tools_cache = data.get("tools", [])
                logger.info(f"Successfully fetched {len(self.tools_cache)} tools from MCP server")
                logger.debug(f"Tools: {[t['name'] for t in self.tools_cache]}")
            except Exception as e:
                logger.error(f"Failed to fetch tools: {str(e)}")
                self.send_error(f"Failed to fetch tools: {str(e)}")
                return []
        return self.tools_cache

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        try:
            response = requests.post(
                f"{MCP_SERVER_URL}/tools/{tool_name}",
                json={"input": arguments},
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                "tool": tool_name,
                "input": arguments,
                "result": f"Error calling tool: {str(e)}",
                "status": "error",
                "timestamp": ""
            }

    def send_response(self, response: Dict[str, Any]):
        """Send JSON-RPC response to Claude Code"""
        print(json.dumps(response), flush=True)

    def send_error(self, message: str, code: int = -32603):
        """Send JSON-RPC error response"""
        self.send_response({
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            },
            "id": None
        })

    def handle_initialize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request - return capabilities only (modern protocol)"""
        logger.info("=== INITIALIZE REQUEST RECEIVED ===")
        logger.debug(f"Initialize request: {request}")

        # Get the protocol version the client is requesting (CRITICAL FIX)
        client_protocol_version = request.get("params", {}).get("protocolVersion", "2024-11-05")
        logger.info(f"Client requested protocol version: {client_protocol_version}")

        # Schema generation moved to handle_list_tools since tools come from tools/list now

        # Modern protocol: initialize response only announces capabilities, no tools
        response = {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": client_protocol_version,  # Echo back client's version
                "capabilities": {
                    "tools": {
                        "listChanged": True  # This tells client to call tools/list next
                    }
                },
                "serverInfo": {
                    "name": "mcp-server-bridge",
                    "version": "1.0.0"
                }
                # Tools are intentionally NOT included here - they come from tools/list
            },
            "id": request.get("id")
        }

        logger.info(f"=== INITIALIZE RESPONSE (MODERN PROTOCOL) ===")
        logger.info("Announcing capabilities only - tools will come from tools/list")
        logger.debug(f"Response: {json.dumps(response, indent=2)}")
        return response

    def handle_list_tools(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request - provide full tool definitions with schemas"""
        logger.info("=== TOOLS/LIST REQUEST ===")
        tools = self.get_tools()
        mcp_tools = []

        for tool in tools:
            # Create detailed input schema for each tool
            input_schema = {
                "type": "object",
                "properties": {},
                "required": []
            }

            # Add parameters based on tool type
            if tool["name"].startswith("postgres_"):
                if "query" in tool["name"]:
                    input_schema["properties"]["query"] = {"type": "string", "description": "SQL query to execute"}
                    input_schema["required"].append("query")
                    input_schema["properties"]["database"] = {"type": "string", "description": "Database name (optional)"}
                elif "list_databases" in tool["name"]:
                    pass  # No parameters needed
                elif "list_tables" in tool["name"]:
                    input_schema["properties"]["schema"] = {"type": "string", "description": "Schema name", "default": "public"}
                    input_schema["properties"]["database"] = {"type": "string", "description": "Database name (optional)"}

            elif tool["name"].startswith("minio_"):
                input_schema["properties"]["bucket_name"] = {"type": "string", "description": "S3 bucket name"}
                input_schema["required"].append("bucket_name")
                if "list_objects" in tool["name"]:
                    input_schema["properties"]["prefix"] = {"type": "string", "description": "Object prefix filter (optional)"}
                elif "get_object" in tool["name"]:
                    input_schema["properties"]["object_name"] = {"type": "string", "description": "Object name/path"}
                    input_schema["required"].append("object_name")

            elif tool["name"] == "search_logs":
                input_schema["properties"]["query"] = {"type": "string", "description": "LogQL query"}
                input_schema["required"].append("query")
                input_schema["properties"]["hours"] = {"type": "integer", "description": "Hours to search back", "default": 1}
                input_schema["properties"]["limit"] = {"type": "integer", "description": "Max results", "default": 100}

            elif tool["name"] == "get_system_metrics":
                input_schema["properties"]["charts"] = {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of metric chart names (optional)"
                }

            elif tool["name"] == "fetch_web_content":
                input_schema["properties"]["url"] = {"type": "string", "description": "URL to fetch"}
                input_schema["required"].append("url")

            elif tool["name"] == "read_file":
                input_schema["properties"]["file_path"] = {"type": "string", "description": "File path to read"}
                input_schema["required"].append("file_path")

            elif tool["name"] == "list_directory":
                input_schema["properties"]["directory_path"] = {"type": "string", "description": "Directory path to list"}
                input_schema["required"].append("directory_path")

            mcp_tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": input_schema
            })

        logger.info(f"Returning {len(mcp_tools)} tools with full schemas")
        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": mcp_tools
            },
            "id": request.get("id")
        }

    def handle_call_tool(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": "Tool name is required"
                },
                "id": request.get("id")
            }

        result = self.call_tool(tool_name, arguments)

        return {
            "jsonrpc": "2.0",
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": result.get("result", str(result))
                    }
                ]
            },
            "id": request.get("id")
        }

    def run(self):
        """Main bridge loop"""
        logger.info("=== MCP BRIDGE STARTING ===")
        logger.info(f"MCP Server URL: {MCP_SERVER_URL}")
        logger.info("Waiting for Claude Code requests...")

        try:
            # Send initialize response immediately
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue

                logger.debug(f"Received request: {line}")

                try:
                    request = json.loads(line)
                    method = request.get("method")
                    logger.info(f"Processing method: {method}")

                    if method == "initialize":
                        response = self.handle_initialize(request)
                        self.send_response(response)
                    elif method == "tools/list":
                        logger.info("=== TOOLS/LIST REQUEST ===")
                        response = self.handle_list_tools(request)
                        self.send_response(response)
                    elif method == "tools/call":
                        logger.info(f"=== TOOLS/CALL REQUEST: {request.get('params', {}).get('name')} ===")
                        response = self.handle_call_tool(request)
                        self.send_response(response)
                    elif method == "notifications/initialized":
                        logger.info("Received 'initialized' notification from client. Handshake complete.")
                        continue  # Simply continue the loop, do not send a response
                    else:
                        logger.warning(f"Unknown method: {method}")
                        self.send_response({
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32601,
                                "message": f"Method not found: {method}"
                            },
                            "id": request.get("id")
                        })

                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {str(e)}")
                    self.send_error(f"Invalid JSON: {str(e)}")
                except Exception as e:
                    logger.error(f"Request handling error: {str(e)}")
                    self.send_error(f"Request handling error: {str(e)}")
                    traceback.print_exc(file=sys.stderr)

        except KeyboardInterrupt:
            logger.info("Bridge interrupted by user")
        except Exception as e:
            logger.error(f"Bridge error: {str(e)}")
            self.send_error(f"Bridge error: {str(e)}")
            traceback.print_exc(file=sys.stderr)

if __name__ == "__main__":
    bridge = MCPBridge()
    bridge.run()