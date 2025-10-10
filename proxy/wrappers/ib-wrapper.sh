#!/bin/bash
# HTTP-to-stdio wrapper for IB MCP service
# Forwards MCP stdio protocol to HTTP JSON-RPC endpoint
set -e

exec python3 -c '
import sys
import json
import urllib.request

MCP_ENDPOINT = "http://mcp-ib:8000/mcp"

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    req = urllib.request.Request(
        MCP_ENDPOINT,
        data=line.encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = response.read().decode("utf-8")
            print(result, flush=True)
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": None
        }
        print(json.dumps(error_response), flush=True)
'
