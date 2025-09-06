#!/usr/bin/env python3
"""Debug MCP server initialization issue"""

import asyncio
import sys
import json
import traceback
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Create server
server = Server("debug-timescaledb")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="test_tool",
            description="Test tool",
            inputSchema={"type": "object", "properties": {}}
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    return [TextContent(type="text", text="Test response")]

async def main():
    print("Starting debug server...", file=sys.stderr)
    
    try:
        # Run with stdio
        async with stdio_server() as (read_stream, write_stream):
            print("Stdio server created", file=sys.stderr)
            # Try different initialization approaches
            try:
                # Approach 1: No initialization_options
                await server.run(read_stream, write_stream)
            except Exception as e:
                print(f"Approach 1 failed: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

if __name__ == "__main__":
    asyncio.run(main())