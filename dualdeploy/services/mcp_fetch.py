#!/usr/bin/env python3
"""
Fetch MCP Service
Provides HTTP fetching with markdown conversion
Native Python implementation using requests library
"""

import os
import sys
import time
import json
import logging
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.mcp_base import MCPService
from services.fetch_models import FetchParams, FetchResponse, HttpMethod

# Third-party imports
try:
    import requests
    from bs4 import BeautifulSoup
    import html2text
except ImportError as e:
    print(f"Error: Missing required dependencies: {e}", file=sys.stderr)
    print("Run: pip install requests beautifulsoup4 html2text", file=sys.stderr)
    sys.exit(1)

class FetchService(MCPService):
    """MCP service for fetching web content"""
    
    def __init__(self):
        super().__init__("fetch", "1.0.0")
        
        # Configure HTML to markdown converter
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        self.html_converter.body_width = 0  # Don't wrap lines
        self.html_converter.unicode_snob = True  # Use unicode
        
        # Register the fetch tool
        self.register_tool(
            "fetch",
            self.fetch_handler,
            FetchParams,
            "Fetch content from a URL with optional markdown conversion"
        )
        
        self.logger.info("Fetch service initialized")
    
    def fetch_handler(self, params: FetchParams) -> Dict[str, Any]:
        """
        Fetch content from a URL
        
        Args:
            params: Validated FetchParams
            
        Returns:
            Dictionary with fetch results
        """
        self.logger.info(f"Fetching {params.method} {params.url}")
        
        # Prepare request parameters
        request_kwargs = {
            'method': params.method.value,
            'url': str(params.url),
            'timeout': params.timeout,
            'allow_redirects': params.follow_redirects,
            'headers': params.headers or {}
        }
        
        # Set User-Agent if not in headers
        if 'User-Agent' not in request_kwargs['headers']:
            request_kwargs['headers']['User-Agent'] = params.user_agent
        
        # Add body for appropriate methods
        if params.body and params.method in [HttpMethod.POST, HttpMethod.PUT, HttpMethod.PATCH]:
            request_kwargs['data'] = params.body
        
        # Track redirects
        redirect_urls = []
        
        # Make the request
        start_time = time.time()
        try:
            response = requests.request(**request_kwargs)
            
            # Track redirect history if redirects were followed
            if params.follow_redirects and hasattr(response, 'history'):
                for hist_response in response.history:
                    if 'Location' in hist_response.headers:
                        redirect_urls.append(hist_response.headers['Location'])
        except requests.exceptions.TooManyRedirects:
            raise ValueError(f"Too many redirects (max {params.max_redirects})")
        except requests.exceptions.Timeout:
            raise ValueError(f"Request timed out after {params.timeout} seconds")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Request failed: {str(e)}")
        
        # Calculate elapsed time
        elapsed_ms = int(response.elapsed.total_seconds() * 1000)
        
        # Get content
        content = response.text
        
        # Convert HTML to markdown if requested and content is HTML
        content_type = response.headers.get('Content-Type', '').lower()
        if params.convert_to_markdown and 'text/html' in content_type:
            try:
                # Parse HTML with BeautifulSoup first for better handling
                soup = BeautifulSoup(content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Convert to markdown
                content = self.html_converter.handle(str(soup))
                
                self.logger.info("Converted HTML to markdown")
            except Exception as e:
                self.logger.warning(f"Failed to convert HTML to markdown: {e}")
                # Keep original HTML content
        
        # Build response
        result = {
            "url": response.url,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content": content,
            "content_type": content_type.split(';')[0] if content_type else "unknown",
            "content_length": len(response.content),
            "elapsed_ms": elapsed_ms,
            "redirects": redirect_urls
        }
        
        self.logger.info(f"Fetch completed: {response.status_code} in {elapsed_ms}ms")
        
        return result

def main():
    """Main entry point for the service"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch MCP Service")
    parser.add_argument("--mode", choices=["stdio", "sse"], default="stdio",
                        help="Run mode: stdio for Claude, sse for web")
    parser.add_argument("--port", type=int, default=8012,
                        help="Port for SSE mode")
    
    args = parser.parse_args()
    
    # Set port in environment for SSE mode
    if args.mode == "sse":
        import os
        os.environ["MCP_SSE_PORT"] = str(args.port)
    
    service = FetchService()
    service.run(args.mode)

if __name__ == "__main__":
    main()