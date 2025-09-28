"""
MCP Playwright Server
Provides browser automation operations via SSE MCP endpoint
"""
import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import aiofiles
from playwright.async_api import async_playwright

app = FastAPI(title="MCP Playwright Server", version="1.0.0")

# Configuration
MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "playwright")
TEMP_PATH = os.getenv("TEMP_PATH", "/tmp")

class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

class MCPTools:
    """MCP tool implementations for browser automation"""

    @staticmethod
    async def navigate_to_page(url: str, wait_for: str = "load") -> Dict[str, Any]:
        """Navigate to a web page and return page information"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Navigate to URL
                response = await page.goto(url, wait_until=wait_for)

                # Get page info
                title = await page.title()
                url_final = page.url
                content = await page.content()

                await browser.close()

                return {
                    "url": url_final,
                    "title": title,
                    "status": response.status if response else "unknown",
                    "content_length": len(content),
                    "success": True
                }
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def take_screenshot(url: str, output_path: str = None, full_page: bool = False) -> Dict[str, Any]:
        """Take a screenshot of a web page"""
        try:
            if not output_path:
                output_path = f"{TEMP_PATH}/screenshot_{asyncio.get_event_loop().time()}.png"
            elif not output_path.startswith('/'):
                output_path = f"{TEMP_PATH}/{output_path}"

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(url, wait_until="networkidle")
                await page.screenshot(path=output_path, full_page=full_page)

                await browser.close()

                return {
                    "url": url,
                    "screenshot_path": output_path,
                    "full_page": full_page,
                    "success": True
                }
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def extract_text(url: str, selector: str = None) -> Dict[str, Any]:
        """Extract text content from a web page"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(url, wait_until="networkidle")

                if selector:
                    # Extract text from specific selector
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                    else:
                        text = None
                        return {"error": f"Selector '{selector}' not found", "success": False}
                else:
                    # Extract all text from body
                    text = await page.evaluate("() => document.body.textContent")

                await browser.close()

                return {
                    "url": url,
                    "selector": selector,
                    "text": text,
                    "text_length": len(text) if text else 0,
                    "success": True
                }
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def click_element(url: str, selector: str, wait_after: int = 1000) -> Dict[str, Any]:
        """Click an element on a web page"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(url, wait_until="networkidle")

                # Wait for element and click
                await page.wait_for_selector(selector, timeout=10000)
                await page.click(selector)

                # Wait after click
                await page.wait_for_timeout(wait_after)

                # Get final URL and title
                final_url = page.url
                title = await page.title()

                await browser.close()

                return {
                    "initial_url": url,
                    "final_url": final_url,
                    "title": title,
                    "selector": selector,
                    "success": True
                }
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def fill_form(url: str, form_data: Dict[str, str]) -> Dict[str, Any]:
        """Fill out a form on a web page"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(url, wait_until="networkidle")

                # Fill form fields
                filled_fields = []
                for selector, value in form_data.items():
                    try:
                        await page.wait_for_selector(selector, timeout=5000)
                        await page.fill(selector, value)
                        filled_fields.append(selector)
                    except Exception as field_error:
                        return {
                            "error": f"Failed to fill field '{selector}': {str(field_error)}",
                            "success": False
                        }

                await browser.close()

                return {
                    "url": url,
                    "filled_fields": filled_fields,
                    "success": True
                }
        except Exception as e:
            return {"error": str(e), "success": False}

    @staticmethod
    async def get_page_info(url: str) -> Dict[str, Any]:
        """Get comprehensive information about a web page"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(url, wait_until="networkidle")

                # Get page info
                title = await page.title()
                final_url = page.url

                # Get meta information
                meta_description = await page.evaluate("""
                    () => {
                        const meta = document.querySelector('meta[name="description"]');
                        return meta ? meta.content : null;
                    }
                """)

                # Count elements
                links_count = await page.evaluate("() => document.querySelectorAll('a').length")
                images_count = await page.evaluate("() => document.querySelectorAll('img').length")
                forms_count = await page.evaluate("() => document.querySelectorAll('form').length")

                await browser.close()

                return {
                    "url": final_url,
                    "title": title,
                    "meta_description": meta_description,
                    "links_count": links_count,
                    "images_count": images_count,
                    "forms_count": forms_count,
                    "success": True
                }
        except Exception as e:
            return {"error": str(e), "success": False}

async def handle_mcp_request(request: MCPRequest) -> MCPResponse:
    """Handle MCP method calls"""

    if request.method == "initialize":
        return MCPResponse(
            result={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "prompts": {},
                    "resources": {}
                },
                "serverInfo": {
                    "name": MCP_SERVER_NAME,
                    "version": "1.0.0"
                }
            },
            id=request.id
        )

    elif request.method == "tools/list":
        tools = [
            {
                "name": "navigate_to_page",
                "description": "Navigate to a web page and get basic information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to navigate to"},
                        "wait_for": {"type": "string", "description": "Wait condition (load, networkidle)", "default": "load"}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "take_screenshot",
                "description": "Take a screenshot of a web page",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to screenshot"},
                        "output_path": {"type": "string", "description": "Output file path (optional)"},
                        "full_page": {"type": "boolean", "description": "Take full page screenshot", "default": False}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "extract_text",
                "description": "Extract text content from a web page",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to extract text from"},
                        "selector": {"type": "string", "description": "CSS selector for specific element (optional)"}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "click_element",
                "description": "Click an element on a web page",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to navigate to"},
                        "selector": {"type": "string", "description": "CSS selector of element to click"},
                        "wait_after": {"type": "integer", "description": "Milliseconds to wait after click", "default": 1000}
                    },
                    "required": ["url", "selector"]
                }
            },
            {
                "name": "fill_form",
                "description": "Fill out form fields on a web page",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL with the form"},
                        "form_data": {
                            "type": "object",
                            "description": "Object with CSS selectors as keys and values to fill",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["url", "form_data"]
                }
            },
            {
                "name": "get_page_info",
                "description": "Get comprehensive information about a web page",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to analyze"}
                    },
                    "required": ["url"]
                }
            }
        ]

        return MCPResponse(result={"tools": tools}, id=request.id)

    elif request.method == "tools/call":
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})

        if tool_name == "navigate_to_page":
            result = await MCPTools.navigate_to_page(**arguments)
        elif tool_name == "take_screenshot":
            result = await MCPTools.take_screenshot(**arguments)
        elif tool_name == "extract_text":
            result = await MCPTools.extract_text(**arguments)
        elif tool_name == "click_element":
            result = await MCPTools.click_element(**arguments)
        elif tool_name == "fill_form":
            result = await MCPTools.fill_form(**arguments)
        elif tool_name == "get_page_info":
            result = await MCPTools.get_page_info(**arguments)
        else:
            return MCPResponse(
                error={"code": -32601, "message": f"Unknown tool: {tool_name}"},
                id=request.id
            )

        return MCPResponse(result={"content": [{"type": "text", "text": json.dumps(result)}]}, id=request.id)

    else:
        return MCPResponse(
            error={"code": -32601, "message": f"Unknown method: {request.method}"},
            id=request.id
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": MCP_SERVER_NAME,
        "temp_path": TEMP_PATH,
        "playwright_ready": True
    }

@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for MCP communication"""

    async def event_stream():
        """Generate SSE events"""
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connection', 'server': MCP_SERVER_NAME})}\n\n"

        try:
            while True:
                # Handle MCP requests from client
                if await request.is_disconnected():
                    break

                # For now, just send periodic ping
                await asyncio.sleep(30)
                yield f"data: {json.dumps({'type': 'ping', 'timestamp': asyncio.get_event_loop().time()})}\n\n"

        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }
    )

@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """HTTP POST endpoint for MCP requests"""
    response = await handle_mcp_request(request)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)