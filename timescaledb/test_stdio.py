#!/usr/bin/env python3
"""Test MCP stdio server basic communication"""

import asyncio
import sys
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server

# Create server
server = Server("test-timescaledb")

@server.list_tools()
async def list_tools():
    return []

async def main():
    print("Starting test server...", file=sys.stderr)
    
    # Run with stdio
    async with stdio_server() as (read_stream, write_stream):
        print("Stdio server created", file=sys.stderr)
        await server.run(
            read_stream,
            write_stream,
            initialization_options={}
        )

if __name__ == "__main__":
    asyncio.run(main())