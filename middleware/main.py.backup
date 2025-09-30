#!/usr/bin/env python3
"""
Simple MCP Tool Injection Middleware
Intercepts /v1/chat/completions and injects MCP tools before forwarding to LiteLLM
"""
import httpx
import json
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Middleware")

# Configuration
LITELLM_URL = "http://litellm:4000"
MCP_PROXY_URL = "http://mcp-proxy:9090"

# Cache for MCP tools (loaded once at startup)
CACHED_TOOLS = None


def fetch_mcp_tools():
    """Fetch available tools from MCP proxy and convert to OpenAI format"""
    try:
        # Get tools from postgres MCP server
        response = httpx.post(
            f"{MCP_PROXY_URL}/postgres/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tools/list",
                "params": {}
            },
            timeout=10.0
        )
        response.raise_for_status()

        mcp_response = response.json()
        tools = mcp_response.get("result", {}).get("tools", [])

        # Convert MCP tools to OpenAI function format
        openai_tools = []
        for tool in tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": f"mcp_postgres_{tool['name']}",
                    "description": tool.get("description", ""),
                    "parameters": tool.get("inputSchema", {
                        "type": "object",
                        "properties": {}
                    })
                }
            }
            openai_tools.append(openai_tool)

        logger.info(f"Loaded {len(openai_tools)} MCP tools from postgres")
        return openai_tools

    except Exception as e:
        logger.error(f"Failed to fetch MCP tools: {e}")
        return []


@app.on_event("startup")
async def startup_event():
    """Load MCP tools once at startup"""
    global CACHED_TOOLS
    CACHED_TOOLS = fetch_mcp_tools()
    logger.info(f"Middleware started with {len(CACHED_TOOLS)} cached tools")


@app.post("/v1/chat/completions")
async def proxy_chat_completions(request: Request):
    """
    Proxy chat completions requests to LiteLLM with MCP tools injected
    """
    try:
        # Parse incoming request
        body = await request.json()

        # Inject MCP tools if not already present
        if "tools" not in body or not body["tools"]:
            if CACHED_TOOLS:
                body["tools"] = CACHED_TOOLS
                logger.info(f"Injected {len(CACHED_TOOLS)} MCP tools into request")

        # Check if streaming is requested
        is_streaming = body.get("stream", False)

        # Forward to LiteLLM
        headers = {
            "Authorization": request.headers.get("Authorization", ""),
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            if is_streaming:
                # Handle streaming response
                async def stream_generator():
                    async with client.stream(
                        "POST",
                        f"{LITELLM_URL}/v1/chat/completions",
                        json=body,
                        headers=headers,
                        timeout=120.0
                    ) as response:
                        async for chunk in response.aiter_bytes():
                            yield chunk

                return StreamingResponse(
                    stream_generator(),
                    media_type="text/event-stream"
                )
            else:
                # Handle non-streaming response
                response = await client.post(
                    f"{LITELLM_URL}/v1/chat/completions",
                    json=body,
                    headers=headers,
                    timeout=120.0
                )

                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )

    except Exception as e:
        logger.error(f"Error proxying request: {e}")
        return Response(
            content=json.dumps({"error": str(e)}),
            status_code=500,
            media_type="application/json"
        )


@app.get("/v1/models")
async def proxy_models(request: Request):
    """Proxy models endpoint to LiteLLM"""
    try:
        headers = {"Authorization": request.headers.get("Authorization", "")}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{LITELLM_URL}/v1/models",
                headers=headers,
                timeout=10.0
            )

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
    except Exception as e:
        logger.error(f"Error proxying models: {e}")
        return Response(
            content=json.dumps({"error": str(e)}),
            status_code=500,
            media_type="application/json"
        )


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "cached_tools": len(CACHED_TOOLS) if CACHED_TOOLS else 0
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)