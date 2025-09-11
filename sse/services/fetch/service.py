#!/usr/bin/env python3
"""
Fetch MCP SSE Service - HTTP content fetching and web scraping with markdown conversion
Implements MCP 2025-06-18 specification with output schemas and enhanced security
"""

import os
import sys
import asyncio
import time
import re
from datetime import datetime
from typing import List, Optional, Any, Dict
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# Add core to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.mcp_sse import MCPSSEServer
from models import (
    FetchUrlInput, FetchWithMarkdownInput, FetchMultipleInput, CheckUrlStatusInput,
    FetchUrlOutput, FetchMarkdownOutput, FetchMultipleOutput, UrlStatusOutput,
    FetchResult, HttpHeaders, HealthOutput, ToolListOutput, ErrorOutput
)


class FetchService:
    """HTTP content fetching and web scraping service"""
    
    def __init__(self):
        self.default_headers = {
            'User-Agent': 'MCP-Fetch-Service/1.0.0 (compatible; AI assistant content fetcher)'
        }
        self.allowed_schemes = {'http', 'https'}
        self.max_content_size = 10 * 1024 * 1024  # 10MB limit
        self.max_redirects = 10
        
    def _is_url_allowed(self, url: str) -> bool:
        """Check if URL scheme is allowed"""
        parsed = urlparse(str(url))
        return parsed.scheme in self.allowed_schemes
    
    def _parse_headers(self, response_headers) -> HttpHeaders:
        """Parse HTTP headers into structured format"""
        headers = HttpHeaders()
        
        # Extract common headers
        headers.content_type = response_headers.get('content-type')
        
        content_length = response_headers.get('content-length')
        if content_length and content_length.isdigit():
            headers.content_length = int(content_length)
        
        headers.last_modified = response_headers.get('last-modified')
        headers.server = response_headers.get('server')
        
        # Store other headers
        headers.custom_headers = {
            k: v for k, v in response_headers.items()
            if k.lower() not in ['content-type', 'content-length', 'last-modified', 'server']
        }
        
        return headers
    
    def _get_request_headers(self, input_headers: Optional[Dict[str, str]], user_agent: Optional[str]) -> Dict[str, str]:
        """Build request headers"""
        headers = self.default_headers.copy()
        
        if user_agent:
            headers['User-Agent'] = user_agent
        
        if input_headers:
            headers.update(input_headers)
        
        return headers

    async def fetch_url(self, input_data: FetchUrlInput) -> FetchUrlOutput:
        """Fetch content from a URL"""
        if not self._is_url_allowed(str(input_data.url)):
            raise ValueError(f"URL scheme not allowed: {input_data.url}")
        
        headers = self._get_request_headers(input_data.headers, input_data.user_agent)
        
        start_time = time.time()
        
        async with httpx.AsyncClient(
            timeout=input_data.timeout,
            follow_redirects=input_data.follow_redirects,
            max_redirects=self.max_redirects
        ) as client:
            try:
                response = await client.get(str(input_data.url), headers=headers)
                response_time = (time.time() - start_time) * 1000
                
                # Check content size
                content_size = len(response.content)
                if content_size > self.max_content_size:
                    raise ValueError(f"Content too large: {content_size} bytes (max {self.max_content_size})")
                
                # Try to decode content
                try:
                    content = response.text
                    encoding = response.encoding or 'utf-8'
                except UnicodeDecodeError:
                    content = response.content.decode('utf-8', errors='ignore')
                    encoding = 'utf-8'
                
                result = FetchResult(
                    url=str(input_data.url),
                    status_code=response.status_code,
                    success=response.is_success,
                    content=content,
                    headers=self._parse_headers(response.headers),
                    response_time_ms=round(response_time, 2),
                    final_url=str(response.url) if response.url != input_data.url else None,
                    content_size=content_size
                )
                
                return FetchUrlOutput(
                    result=result,
                    encoding=encoding,
                    timestamp=datetime.utcnow().isoformat()
                )
                
            except httpx.RequestError as e:
                response_time = (time.time() - start_time) * 1000
                
                result = FetchResult(
                    url=str(input_data.url),
                    status_code=0,
                    success=False,
                    headers=HttpHeaders(),
                    response_time_ms=round(response_time, 2),
                    error_message=str(e)
                )
                
                return FetchUrlOutput(
                    result=result,
                    encoding='utf-8',
                    timestamp=datetime.utcnow().isoformat()
                )

    async def fetch_with_markdown(self, input_data: FetchWithMarkdownInput) -> FetchMarkdownOutput:
        """Fetch URL content and convert to markdown"""
        if not self._is_url_allowed(str(input_data.url)):
            raise ValueError(f"URL scheme not allowed: {input_data.url}")
        
        headers = self._get_request_headers(None, input_data.user_agent)
        
        start_time = time.time()
        
        async with httpx.AsyncClient(
            timeout=input_data.timeout,
            follow_redirects=input_data.follow_redirects,
            max_redirects=self.max_redirects
        ) as client:
            try:
                response = await client.get(str(input_data.url), headers=headers)
                response_time = (time.time() - start_time) * 1000
                
                # Check content size
                content_size = len(response.content)
                if content_size > self.max_content_size:
                    raise ValueError(f"Content too large: {content_size} bytes (max {self.max_content_size})")
                
                html_content = response.text
                
                # Parse HTML with BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                
                conversion_info = {
                    "original_size": len(html_content),
                    "converted_links": 0,
                    "removed_elements": 0
                }
                
                # Remove scripts and styles if requested
                if input_data.strip_scripts:
                    scripts = soup.find_all(['script', 'style', 'noscript'])
                    conversion_info["removed_elements"] = len(scripts)
                    for script in scripts:
                        script.decompose()
                
                # Convert relative links to absolute if requested
                if input_data.convert_links:
                    base_url = str(response.url)
                    links = soup.find_all(['a', 'img', 'link'], href=True) + soup.find_all('img', src=True)
                    
                    for link in links:
                        attr = 'href' if link.get('href') else 'src'
                        if link.get(attr):
                            absolute_url = urljoin(base_url, link[attr])
                            link[attr] = absolute_url
                            conversion_info["converted_links"] += 1
                
                # Convert to markdown
                markdown_content = md(str(soup), heading_style="ATX", bullets="-")
                
                conversion_info["markdown_size"] = len(markdown_content)
                conversion_info["compression_ratio"] = round(
                    len(markdown_content) / len(html_content), 3
                ) if len(html_content) > 0 else 0
                
                result = FetchResult(
                    url=str(input_data.url),
                    status_code=response.status_code,
                    success=response.is_success,
                    content=html_content,
                    headers=self._parse_headers(response.headers),
                    response_time_ms=round(response_time, 2),
                    final_url=str(response.url) if response.url != input_data.url else None,
                    content_size=content_size
                )
                
                return FetchMarkdownOutput(
                    result=result,
                    markdown_content=markdown_content,
                    conversion_info=conversion_info,
                    timestamp=datetime.utcnow().isoformat()
                )
                
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                
                result = FetchResult(
                    url=str(input_data.url),
                    status_code=0,
                    success=False,
                    headers=HttpHeaders(),
                    response_time_ms=round(response_time, 2),
                    error_message=str(e)
                )
                
                return FetchMarkdownOutput(
                    result=result,
                    markdown_content="",
                    conversion_info={"error": str(e)},
                    timestamp=datetime.utcnow().isoformat()
                )

    async def fetch_multiple(self, input_data: FetchMultipleInput) -> FetchMultipleOutput:
        """Fetch content from multiple URLs"""
        if len(input_data.urls) > 10:
            raise ValueError("Maximum 10 URLs allowed per request")
        
        start_time = time.time()
        results = []
        
        async with httpx.AsyncClient(
            timeout=input_data.timeout,
            follow_redirects=input_data.follow_redirects,
            max_redirects=self.max_redirects
        ) as client:
            
            for url in input_data.urls:
                if not self._is_url_allowed(str(url)):
                    if input_data.fail_fast:
                        raise ValueError(f"URL scheme not allowed: {url}")
                    continue
                
                try:
                    url_start_time = time.time()
                    response = await client.get(str(url), headers=self.default_headers)
                    response_time = (time.time() - url_start_time) * 1000
                    
                    content_size = len(response.content)
                    content = response.text if content_size <= self.max_content_size else None
                    
                    result = FetchResult(
                        url=str(url),
                        status_code=response.status_code,
                        success=response.is_success,
                        content=content,
                        headers=self._parse_headers(response.headers),
                        response_time_ms=round(response_time, 2),
                        final_url=str(response.url) if response.url != url else None,
                        content_size=content_size
                    )
                    
                    results.append(result)
                    
                except Exception as e:
                    url_response_time = (time.time() - url_start_time) * 1000
                    
                    error_result = FetchResult(
                        url=str(url),
                        status_code=0,
                        success=False,
                        headers=HttpHeaders(),
                        response_time_ms=round(url_response_time, 2),
                        error_message=str(e)
                    )
                    
                    results.append(error_result)
                    
                    if input_data.fail_fast:
                        break
        
        total_time = (time.time() - start_time) * 1000
        successful = sum(1 for r in results if r.success)
        
        return FetchMultipleOutput(
            results=results,
            total_urls=len(input_data.urls),
            successful_urls=successful,
            failed_urls=len(results) - successful,
            total_time_ms=round(total_time, 2),
            timestamp=datetime.utcnow().isoformat()
        )

    async def check_url_status(self, input_data: CheckUrlStatusInput) -> UrlStatusOutput:
        """Check URL status without fetching full content"""
        if not self._is_url_allowed(str(input_data.url)):
            raise ValueError(f"URL scheme not allowed: {input_data.url}")
        
        start_time = time.time()
        redirects = []
        
        async with httpx.AsyncClient(
            timeout=input_data.timeout,
            follow_redirects=True,
            max_redirects=self.max_redirects
        ) as client:
            try:
                # Track redirects manually
                current_url = str(input_data.url)
                
                response = await client.request(
                    input_data.method,
                    current_url,
                    headers=self.default_headers
                )
                
                response_time = (time.time() - start_time) * 1000
                
                # Check for redirects
                if str(response.url) != current_url:
                    redirects.append(str(response.url))
                
                # Get SSL info for HTTPS URLs
                ssl_info = None
                if str(input_data.url).startswith('https'):
                    ssl_info = {
                        "verified": True,  # httpx verifies by default
                        "protocol": "TLS"
                    }
                
                return UrlStatusOutput(
                    url=str(input_data.url),
                    status_code=response.status_code,
                    reachable=response.is_success,
                    response_time_ms=round(response_time, 2),
                    headers=self._parse_headers(response.headers),
                    redirects=redirects,
                    ssl_info=ssl_info,
                    timestamp=datetime.utcnow().isoformat()
                )
                
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                
                return UrlStatusOutput(
                    url=str(input_data.url),
                    status_code=0,
                    reachable=False,
                    response_time_ms=round(response_time, 2),
                    headers=HttpHeaders(),
                    redirects=[],
                    error_message=str(e),
                    timestamp=datetime.utcnow().isoformat()
                )

    async def test_external_connectivity(self) -> bool:
        """Test if external HTTP connectivity is available"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.head("https://httpbin.org/status/200")
                return response.status_code == 200
        except:
            return False


async def create_mcp_server() -> MCPSSEServer:
    """Create and configure the fetch MCP SSE server"""
    
    # Initialize service
    fetch_service = FetchService()
    
    # Create server with service info
    server = MCPSSEServer(
        name="fetch",
        version="1.0.0",
        port=int(os.getenv('SERVICE_PORT', 8002))
    )
    
    # Register tools with input/output schemas
    server.register_tool(
        name="fetch_url",
        handler=fetch_service.fetch_url,
        input_schema=FetchUrlInput,
        output_schema=FetchUrlOutput,
        description="Fetch content from a URL with configurable options"
    )
    
    server.register_tool(
        name="fetch_with_markdown",
        handler=fetch_service.fetch_with_markdown,
        input_schema=FetchWithMarkdownInput,
        output_schema=FetchMarkdownOutput,
        description="Fetch URL content and convert HTML to markdown"
    )
    
    server.register_tool(
        name="fetch_multiple",
        handler=fetch_service.fetch_multiple,
        input_schema=FetchMultipleInput,
        output_schema=FetchMultipleOutput,
        description="Fetch content from multiple URLs efficiently"
    )
    
    server.register_tool(
        name="check_url_status",
        handler=fetch_service.check_url_status,
        input_schema=CheckUrlStatusInput,
        output_schema=UrlStatusOutput,
        description="Check URL availability and response status without fetching content"
    )
    
    return server


async def main():
    """Main entry point"""
    try:
        server = await create_mcp_server()
        await server.run_async()
    except Exception as e:
        print(f"Failed to start fetch service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())