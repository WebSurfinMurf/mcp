#!/usr/bin/env python3
"""
MCP HTTP Bridge for n8n Service
Connects Codex to HTTP-based MCP servers via stdio transport
"""
import json
import sys
import requests
import asyncio

MCP_HTTP_ENDPOINT = "http://127.0.0.1:9074/mcp"

async def handle_request(request_data):
    """Forward MCP request to HTTP endpoint"""
    try:
        response = requests.post(
            MCP_HTTP_ENDPOINT,
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        error_msg = f"HTTP bridge error: {str(e)}"

        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": error_msg
            },
            "id": request_data.get("id")
        }

async def main():
    """Main stdio MCP bridge loop"""
    while True:
        try:
            # Read JSON-RPC request from stdin
            line = sys.stdin.readline()
            if not line:
                break

            request_data = json.loads(line.strip())

            # Forward to HTTP endpoint
            response_data = await handle_request(request_data)

            # Send response to stdout
            print(json.dumps(response_data))
            sys.stdout.flush()

        except json.JSONDecodeError:
            # Invalid JSON, send error response
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                },
                "id": None
            }
            print(json.dumps(error_response))
            sys.stdout.flush()
        except Exception as e:
            # Other errors
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                },
                "id": None
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main())