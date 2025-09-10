#!/usr/bin/env python3
"""
Pydantic models for Fetch MCP Service
Validates and structures input parameters
"""

from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional, Literal
from enum import Enum

class HttpMethod(str, Enum):
    """Supported HTTP methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"

class FetchParams(BaseModel):
    """Parameters for fetch tool"""
    url: HttpUrl = Field(
        ..., 
        description="The URL to fetch content from"
    )
    method: HttpMethod = Field(
        default=HttpMethod.GET,
        description="HTTP method to use"
    )
    headers: Optional[dict] = Field(
        default=None,
        description="Optional HTTP headers"
    )
    body: Optional[str] = Field(
        default=None,
        description="Request body for POST/PUT/PATCH requests"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds"
    )
    follow_redirects: bool = Field(
        default=True,
        description="Whether to follow HTTP redirects"
    )
    max_redirects: int = Field(
        default=10,
        ge=0,
        le=20,
        description="Maximum number of redirects to follow"
    )
    convert_to_markdown: bool = Field(
        default=True,
        description="Convert HTML responses to markdown"
    )
    user_agent: Optional[str] = Field(
        default="MCP-Fetch/1.0",
        description="User-Agent header value"
    )
    
    @validator('body')
    def validate_body_with_method(cls, v, values):
        """Ensure body is only used with appropriate methods"""
        method = values.get('method', HttpMethod.GET)
        if v and method in [HttpMethod.GET, HttpMethod.HEAD, HttpMethod.OPTIONS]:
            raise ValueError(f"Body not allowed for {method} requests")
        return v
    
    @validator('headers')
    def validate_headers(cls, v):
        """Ensure headers are properly formatted"""
        if v:
            # Convert all header values to strings
            return {k: str(v) for k, v in v.items()}
        return v

class FetchResponse(BaseModel):
    """Response structure for fetch tool"""
    url: str = Field(description="Final URL after redirects")
    status_code: int = Field(description="HTTP status code")
    headers: dict = Field(description="Response headers")
    content: str = Field(description="Response content (possibly converted to markdown)")
    content_type: str = Field(description="Content-Type of response")
    content_length: Optional[int] = Field(description="Content length in bytes")
    elapsed_ms: int = Field(description="Request duration in milliseconds")
    redirects: list[str] = Field(default_factory=list, description="List of redirect URLs")