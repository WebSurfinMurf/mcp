"""
Pydantic models for MCP SSE protocol
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class MCPRequest(BaseModel):
    """Base MCP request model"""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name (e.g., 'tools/call')")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Method parameters")
    id: Optional[Union[str, int]] = Field(default=None, description="Request ID")


class MCPResponse(BaseModel):
    """Base MCP response model"""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: Optional[Union[str, int]] = Field(default=None, description="Request ID")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Success result")
    error: Optional[Dict[str, Any]] = Field(default=None, description="Error information")


class MCPError(BaseModel):
    """MCP error model"""
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional error data")


class ToolCall(BaseModel):
    """Tool call request"""
    name: str = Field(..., description="Tool name")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ToolResult(BaseModel):
    """Tool execution result"""
    content: List[Dict[str, Any]] = Field(default_factory=list, description="Result content")
    isError: bool = Field(default=False, description="Whether this is an error result")


class ServiceInfo(BaseModel):
    """Service information model"""
    name: str = Field(..., description="Service name")
    version: str = Field(default="1.0.0", description="Service version")
    protocol_version: str = Field(default="2024-11-05", description="MCP protocol version")
    port: int = Field(..., description="Service port")
    uptime: float = Field(default=0.0, description="Service uptime in seconds")
    tools_count: int = Field(default=0, description="Number of registered tools")


class ToolSchema(BaseModel):
    """Tool schema definition for MCP 2025-06-18"""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    inputSchema: Dict[str, Any] = Field(..., description="JSON Schema for tool input")
    outputSchema: Optional[Dict[str, Any]] = Field(default=None, description="JSON Schema for tool output (MCP 2025-06-18)")


class ElicitationRequest(BaseModel):
    """Server-initiated request for additional information (MCP 2025-06-18)"""
    type: str = Field(default="elicitation", description="Request type")
    prompt: str = Field(..., description="Prompt for user input")
    schema: Optional[Dict[str, Any]] = Field(default=None, description="Expected response schema")


class UserConsent(BaseModel):
    """User consent information for MCP 2025-06-18"""
    granted: bool = Field(..., description="Whether consent was granted")
    scope: List[str] = Field(default_factory=list, description="Scope of consent granted")
    timestamp: datetime = Field(default_factory=datetime.now, description="When consent was granted")


class EndpointCapabilities(BaseModel):
    """Service endpoint capabilities"""
    endpoints: List[ToolSchema] = Field(default_factory=list, description="Available tools")


class HealthStatus(BaseModel):
    """Service health status"""
    status: str = Field(..., description="Health status (healthy/unhealthy)")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    uptime: float = Field(..., description="Uptime in seconds")
    tools_count: int = Field(..., description="Number of registered tools")
    timestamp: datetime = Field(default_factory=datetime.now, description="Status timestamp")


class SSEEvent(BaseModel):
    """Server-Sent Event model"""
    event: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(..., description="Event data")
    id: Optional[str] = Field(default=None, description="Event ID")
    retry: Optional[int] = Field(default=None, description="Retry interval in ms")