#!/usr/bin/env python3
"""
MCP Tool Injection Middleware v3 - All MCP Servers with Tool Listing
Handles multiple MCP servers and provides a special list_tools capability
"""
import httpx
import json
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import logging
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Middleware v3")

# Configuration
LITELLM_URL = "http://litellm:4000"
MCP_PROXY_URL = "http://mcp-proxy:9090"
MAX_TOOL_ITERATIONS = 5

# MCP server endpoints (from proxy config)
MCP_SERVERS = {
    "filesystem": "/filesystem/mcp",
    "postgres": "/postgres/mcp",
    "puppeteer": "/puppeteer/mcp",
    "memory": "/memory/mcp",
    "minio": "/minio/mcp",
    "n8n": "/n8n/mcp",
    "timescaledb": "/timescaledb/mcp"
}

# Cache for MCP tools organized by server
CACHED_TOOLS_BY_SERVER: Dict[str, List[dict]] = {}
ALL_TOOLS: List[dict] = []


def fetch_tools_from_server(server_name: str, endpoint: str):
    """Fetch tools from a specific MCP server"""
    try:
        response = httpx.post(
            f"{MCP_PROXY_URL}{endpoint}",
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
                    "name": f"mcp_{server_name}_{tool['name']}",
                    "description": f"[{server_name.upper()}] {tool.get('description', '')}",
                    "parameters": tool.get("inputSchema", {
                        "type": "object",
                        "properties": {}
                    })
                },
                "_mcp_server": server_name,
                "_original_name": tool['name']
            }
            openai_tools.append(openai_tool)

        logger.info(f"Loaded {len(openai_tools)} tools from {server_name}")
        return openai_tools

    except Exception as e:
        logger.error(f"Failed to fetch tools from {server_name}: {e}")
        return []


def load_all_mcp_tools():
    """Load tools from all MCP servers"""
    global CACHED_TOOLS_BY_SERVER, ALL_TOOLS

    CACHED_TOOLS_BY_SERVER = {}
    ALL_TOOLS = []

    for server_name, endpoint in MCP_SERVERS.items():
        tools = fetch_tools_from_server(server_name, endpoint)
        CACHED_TOOLS_BY_SERVER[server_name] = tools
        ALL_TOOLS.extend(tools)

    # Add special list_tools function
    list_tools_function = {
        "type": "function",
        "function": {
            "name": "mcp_list_all_tools",
            "description": "List all available MCP tools organized by server. Use this when user asks to 'list tools' or 'show available tools'.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        "_mcp_server": "middleware",
        "_original_name": "list_all_tools"
    }
    ALL_TOOLS.append(list_tools_function)

    total_tools = sum(len(tools) for tools in CACHED_TOOLS_BY_SERVER.values())
    logger.info(f"Loaded {total_tools} tools from {len(CACHED_TOOLS_BY_SERVER)} MCP servers")
    return ALL_TOOLS


def execute_mcp_tool(tool_name: str, arguments: dict):
    """Execute an MCP tool"""
    try:
        # Handle special list_tools command
        if tool_name == "mcp_list_all_tools":
            return generate_tools_list()

        # Parse tool name to extract server and actual tool name
        parts = tool_name.split("_", 2)  # mcp_servername_toolname
        if len(parts) < 3:
            return json.dumps({"error": f"Invalid tool name format: {tool_name}"})

        server_name = parts[1]
        actual_tool_name = parts[2]

        if server_name not in MCP_SERVERS:
            return json.dumps({"error": f"Unknown MCP server: {server_name}"})

        logger.info(f"Executing {server_name}/{actual_tool_name} with args: {arguments}")

        # Call MCP proxy
        endpoint = MCP_SERVERS[server_name]
        response = httpx.post(
            f"{MCP_PROXY_URL}{endpoint}",
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

        logger.info(f"Tool execution successful: {str(result)[:200]}")
        return json.dumps(result)

    except Exception as e:
        logger.error(f"Failed to execute tool {tool_name}: {e}")
        return json.dumps({"error": str(e)})


def generate_tools_list():
    """Generate a formatted list of all MCP tools organized by server"""
    output = "# Available MCP Tools\n\n"

    for server_name in sorted(CACHED_TOOLS_BY_SERVER.keys()):
        tools = CACHED_TOOLS_BY_SERVER[server_name]
        if tools:
            output += f"## {server_name.upper()} ({len(tools)} tools)\n\n"
            output += "| Tool Name | Description |\n"
            output += "|-----------|-------------|\n"

            for tool in tools:
                func = tool["function"]
                tool_name = func["name"].replace(f"mcp_{server_name}_", "")
                desc = func["description"].replace(f"[{server_name.upper()}] ", "")
                # Truncate long descriptions
                if len(desc) > 80:
                    desc = desc[:77] + "..."
                output += f"| `{tool_name}` | {desc} |\n"

            output += "\n"

    output += f"\n**Total: {sum(len(tools) for tools in CACHED_TOOLS_BY_SERVER.values())} tools across {len(CACHED_TOOLS_BY_SERVER)} MCP servers**"

    return json.dumps({
        "content": [{
            "type": "text",
            "text": output
        }]
    })


@app.on_event("startup")
async def startup_event():
    """Load all MCP tools at startup"""
    load_all_mcp_tools()
    logger.info(f"Middleware v3 started with {len(ALL_TOOLS)} total tools")


@app.post("/v1/chat/completions")
async def proxy_chat_completions(request: Request):
    """Proxy chat completions with automatic tool execution loop"""
    try:
        body = await request.json()

        # Strip -mcp suffix from model name if present
        if "model" in body and body["model"].endswith("-mcp"):
            body["model"] = body["model"][:-4]

        # Inject all MCP tools
        if "tools" not in body or not body["tools"]:
            if ALL_TOOLS:
                body["tools"] = ALL_TOOLS
                logger.info(f"Injected {len(ALL_TOOLS)} MCP tools")

        # Disable streaming for tool execution
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

                # Check for tool calls
                tool_calls = message.get("tool_calls", [])

                if not tool_calls or finish_reason != "tool_calls":
                    logger.info("No tool calls, returning final response")
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

                # Add assistant message and tool results to conversation
                body["messages"].append(message)
                body["messages"].extend(tool_messages)

            # Max iterations reached
            logger.warning(f"Max tool iterations ({MAX_TOOL_ITERATIONS}) reached")
            return Response(
                content=json.dumps({"error": "Max tool execution iterations reached"}),
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
    """Proxy models endpoint to LiteLLM with MCP suffix"""
    try:
        headers = {"Authorization": request.headers.get("Authorization", "")}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{LITELLM_URL}/v1/models",
                headers=headers,
                timeout=10.0
            )

            # Modify model names to include MCP suffix
            models_data = response.json()
            if "data" in models_data:
                for model in models_data["data"]:
                    model["id"] = f"{model['id']}-mcp"

            return Response(
                content=json.dumps(models_data),
                status_code=response.status_code,
                media_type="application/json"
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
        "version": "v3-all-mcp-servers",
        "mcp_servers": len(CACHED_TOOLS_BY_SERVER),
        "total_tools": len(ALL_TOOLS),
        "tools_by_server": {
            server: len(tools)
            for server, tools in CACHED_TOOLS_BY_SERVER.items()
        }
    }


@app.post("/reload")
async def reload_tools():
    """Reload all MCP tools"""
    load_all_mcp_tools()
    return {
        "status": "reloaded",
        "total_tools": len(ALL_TOOLS),
        "servers": list(CACHED_TOOLS_BY_SERVER.keys())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)