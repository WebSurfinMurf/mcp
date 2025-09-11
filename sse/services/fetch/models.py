"""
Fetch Service Models - Pydantic schemas with MCP 2025-06-18 output schemas
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, HttpUrl


# Input Models
class FetchUrlInput(BaseModel):
    """Input schema for fetching URL content"""
    url: HttpUrl = Field(..., description="URL to fetch content from")
    timeout: int = Field(30, description="Request timeout in seconds", ge=1, le=120)
    follow_redirects: bool = Field(True, description="Whether to follow HTTP redirects")
    user_agent: Optional[str] = Field(None, description="Custom User-Agent header")
    headers: Optional[Dict[str, str]] = Field(None, description="Additional HTTP headers")


class FetchWithMarkdownInput(BaseModel):
    """Input schema for fetching URL and converting to markdown"""
    url: HttpUrl = Field(..., description="URL to fetch and convert to markdown")
    timeout: int = Field(30, description="Request timeout in seconds", ge=1, le=120)
    follow_redirects: bool = Field(True, description="Whether to follow HTTP redirects")
    user_agent: Optional[str] = Field(None, description="Custom User-Agent header")
    strip_scripts: bool = Field(True, description="Remove script and style tags")
    convert_links: bool = Field(True, description="Convert relative to absolute links")


class FetchMultipleInput(BaseModel):
    """Input schema for fetching multiple URLs"""
    urls: List[HttpUrl] = Field(..., description="List of URLs to fetch", max_items=10)
    timeout: int = Field(30, description="Request timeout per URL in seconds", ge=1, le=120)
    follow_redirects: bool = Field(True, description="Whether to follow HTTP redirects")
    fail_fast: bool = Field(False, description="Stop on first error")


class CheckUrlStatusInput(BaseModel):
    """Input schema for checking URL status"""
    url: HttpUrl = Field(..., description="URL to check status")
    timeout: int = Field(10, description="Request timeout in seconds", ge=1, le=60)
    method: str = Field("HEAD", description="HTTP method to use", pattern="^(HEAD|GET)$")


# Output Models (MCP 2025-06-18)
class HttpHeaders(BaseModel):
    """HTTP headers structure"""
    content_type: Optional[str] = None
    content_length: Optional[int] = None
    last_modified: Optional[str] = None
    server: Optional[str] = None
    custom_headers: Dict[str, str] = {}


class FetchResult(BaseModel):
    """Individual fetch result structure"""
    url: str
    status_code: int
    success: bool
    content: Optional[str] = None
    headers: HttpHeaders
    response_time_ms: float
    final_url: Optional[str] = None  # After redirects
    error_message: Optional[str] = None
    content_size: int = 0


class FetchUrlOutput(BaseModel):
    """Output schema for URL fetch operations"""
    result: FetchResult
    encoding: str
    timestamp: str


class FetchMarkdownOutput(BaseModel):
    """Output schema for markdown conversion"""
    result: FetchResult
    markdown_content: str
    conversion_info: Dict[str, Any]
    timestamp: str


class FetchMultipleOutput(BaseModel):
    """Output schema for multiple URL fetching"""
    results: List[FetchResult]
    total_urls: int
    successful_urls: int
    failed_urls: int
    total_time_ms: float
    timestamp: str


class UrlStatusOutput(BaseModel):
    """Output schema for URL status checks"""
    url: str
    status_code: int
    reachable: bool
    response_time_ms: float
    headers: HttpHeaders
    redirects: List[str]
    ssl_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    timestamp: str


class HealthOutput(BaseModel):
    """Health check output schema"""
    status: str
    service: str
    version: str
    uptime: float
    tools_count: int
    external_connectivity: bool
    timestamp: str


class ToolListOutput(BaseModel):
    """Tool listing output schema"""
    tools: List[Dict[str, Any]]
    service: str
    version: str


class ErrorOutput(BaseModel):
    """Error response schema"""
    error: str
    details: Optional[str] = None
    error_code: Optional[str] = None