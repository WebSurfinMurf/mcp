"""
MCP protocol implementation for SSE services
"""

import json
import logging
from typing import Dict, Any, Optional
from core.models import MCPRequest, MCPResponse, MCPError, ToolCall, ToolResult

logger = logging.getLogger(__name__)


class MCPProtocolHandler:
    """Handles MCP protocol messages and routing"""
    
    def __init__(self):
        self.handlers = {
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
        }
        self.tools = {}
    
    def register_tool(self, name: str, handler: callable, input_schema: dict, description: str, output_schema: dict = None):
        """Register a tool with the protocol handler (MCP 2025-06-18)"""
        self.tools[name] = {
            "handler": handler,
            "input_schema": input_schema,
            "output_schema": output_schema,
            "description": description
        }
        logger.info(f"Registered tool: {name} (MCP 2025-06-18)")
    
    def get_tool_list(self) -> list:
        """Get list of available tools (MCP 2025-06-18 with output schemas)"""
        tools = []
        for name, tool_data in self.tools.items():
            tool_def = {
                "name": name,
                "description": tool_data["description"],
                "inputSchema": tool_data["input_schema"]
            }
            # Add output schema if available (MCP 2025-06-18 feature)
            if tool_data.get("output_schema"):
                tool_def["outputSchema"] = tool_data["output_schema"]
            tools.append(tool_def)
        return tools
    
    async def handle_request(self, request_data: dict) -> dict:
        """Handle incoming MCP request"""
        try:
            request = MCPRequest(**request_data)
            
            if request.method not in self.handlers:
                return self._create_error_response(
                    request.id,
                    -32601,
                    f"Method not found: {request.method}"
                )
            
            handler = self.handlers[request.method]
            result = await handler(request)
            
            return MCPResponse(
                id=request.id,
                result=result
            ).dict()
            
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return self._create_error_response(
                request_data.get("id"),
                -32603,
                f"Internal error: {str(e)}"
            )
    
    async def _handle_tools_list(self, request: MCPRequest) -> dict:
        """Handle tools/list request"""
        return {
            "tools": self.get_tool_list()
        }
    
    async def _handle_tools_call(self, request: MCPRequest) -> dict:
        """Handle tools/call request"""
        if not request.params:
            raise ValueError("Missing parameters for tools/call")
        
        tool_call = ToolCall(**request.params)
        
        if tool_call.name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_call.name}")
        
        tool_data = self.tools[tool_call.name]
        handler = tool_data["handler"]
        
        try:
            # Execute the tool
            result = await handler(**tool_call.arguments)
            
            # Ensure result is properly formatted
            if isinstance(result, dict) and "content" in result:
                return result
            else:
                # Wrap simple results in MCP format
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": str(result)
                        }
                    ]
                }
                
        except Exception as e:
            logger.error(f"Tool execution error for {tool_call.name}: {e}")
            return {
                "content": [
                    {
                        "type": "text", 
                        "text": f"Error: {str(e)}"
                    }
                ],
                "isError": True
            }
    
    def _create_error_response(self, request_id: Optional[str], code: int, message: str) -> dict:
        """Create an error response"""
        return MCPResponse(
            id=request_id,
            error=MCPError(
                code=code,
                message=message
            ).dict()
        ).dict()