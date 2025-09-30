#!/usr/bin/env python3
"""
MCP Tool Injection Middleware with Automatic Tool Execution
Handles the full tool execution loop so Open WebUI gets final answers
"""
import httpx
import json
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Middleware v2")

# Configuration
LITELLM_URL = "http://litellm:4000"
MCP_PROXY_URL = "http://mcp-proxy:9090"
MAX_TOOL_ITERATIONS = 5

# Cache for MCP tools
CACHED_TOOLS = None


def fetch_mcp_tools():
    """Fetch available tools from MCP proxy and convert to OpenAI format"""
    try:
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


def execute_mcp_tool(tool_name: str, arguments: dict):
    """Execute an MCP tool and return the result"""
    try:
        # Extract actual tool name (remove mcp_postgres_ prefix)
        actual_tool_name = tool_name.replace("mcp_postgres_", "")

        logger.info(f"Executing MCP tool: {actual_tool_name} with args: {arguments}")

        # Call MCP proxy
        response = httpx.post(
            f"{MCP_PROXY_URL}/postgres/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "tool_call",
                "method": "tools/call",
                "params": {
                    "name": actual_tool_name,
                    "arguments": arguments
                }
            },
            timeout=30.0
        )
        response.raise_for_status()

        mcp_response = response.json()
        result = mcp_response.get("result", {})

        logger.info(f"Tool execution result: {str(result)[:200]}")
        return json.dumps(result)

    except Exception as e:
        logger.error(f"Failed to execute MCP tool {tool_name}: {e}")
        return json.dumps({"error": str(e)})


@app.on_event("startup")
async def startup_event():
    """Load MCP tools once at startup"""
    global CACHED_TOOLS
    CACHED_TOOLS = fetch_mcp_tools()
    logger.info(f"Middleware started with {len(CACHED_TOOLS)} cached tools")


@app.post("/v1/chat/completions")
async def proxy_chat_completions(request: Request):
    """
    Proxy chat completions with automatic tool execution loop
    """
    try:
        body = await request.json()
        messages = body.get("messages", [])

        # Inject MCP tools
        if "tools" not in body or not body["tools"]:
            if CACHED_TOOLS:
                body["tools"] = CACHED_TOOLS
                logger.info(f"Injected {len(CACHED_TOOLS)} MCP tools")

        # Disable streaming for tool execution (we need full responses)
        original_stream = body.get("stream", False)
        body["stream"] = False

        headers = {
            "Authorization": request.headers.get("Authorization", ""),
            "Content-Type": "application/json"
        }

        # Tool execution loop
        iteration = 0
        async with httpx.AsyncClient() as client:
            while iteration < MAX_TOOL_ITERATIONS:
                iteration += 1
                logger.info(f"Tool loop iteration {iteration}")

                # Call LiteLLM
                response = await client.post(
                    f"{LITELLM_URL}/v1/chat/completions",
                    json=body,
                    headers=headers,
                    timeout=120.0
                )

                result = response.json()
                choice = result.get("choices", [{}])[0]
                message = choice.get("message", {})
                finish_reason = choice.get("finish_reason")

                # Check if there are tool calls
                tool_calls = message.get("tool_calls", [])

                if not tool_calls or finish_reason != "tool_calls":
                    # No more tools to execute, return final response
                    logger.info("No tool calls, returning final response")
                    if original_stream:
                        # Convert to streaming format if originally requested
                        # For now, just return as-is
                        pass
                    return Response(
                        content=response.content,
                        status_code=response.status_code,
                        headers=dict(response.headers)
                    )

                # Execute all tool calls
                logger.info(f"Executing {len(tool_calls)} tool calls")
                tool_messages = []

                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])
                    tool_id = tool_call["id"]

                    # Execute tool
                    tool_result = execute_mcp_tool(tool_name, tool_args)

                    # Add tool result to messages
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": tool_result
                    })

                # Add assistant message with tool calls and tool results to conversation
                body["messages"].append(message)
                body["messages"].extend(tool_messages)

            # Max iterations reached
            logger.warning(f"Max tool iterations ({MAX_TOOL_ITERATIONS}) reached")
            return Response(
                content=json.dumps({
                    "error": "Max tool execution iterations reached"
                }),
                status_code=500,
                media_type="application/json"
            )

    except Exception as e:
        logger.error(f"Error in proxy: {e}", exc_info=True)
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
        "cached_tools": len(CACHED_TOOLS) if CACHED_TOOLS else 0,
        "version": "v2-with-tool-execution"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)