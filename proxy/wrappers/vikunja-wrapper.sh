#!/bin/bash
# HTTP-to-stdio wrapper for Vikunja MCP service (FastMCP streamable-http)
# Forwards MCP stdio protocol to HTTP SSE endpoint, strips SSE framing
set -e

exec python3 -c '
import sys
import json
import urllib.request

MCP_ENDPOINT = "http://mcp-vikunja:8000/mcp"

# Session ID is tracked across requests per the streamable-http spec
session_id = None

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    req = urllib.request.Request(
        MCP_ENDPOINT,
        data=line.encode("utf-8"),
        headers=headers,
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            # Capture session ID from response headers
            new_session = response.headers.get("Mcp-Session-Id")
            if new_session:
                session_id = new_session

            raw = response.read().decode("utf-8")
            # SSE framing: lines starting with "data: " contain the JSON payload
            for l in raw.splitlines():
                if l.startswith("data: "):
                    print(l[6:], flush=True)
                    break
            else:
                # Plain JSON fallback (non-SSE response)
                if raw.strip():
                    print(raw.strip(), flush=True)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else str(e)
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": f"HTTP {e.code}: {body}"},
            "id": None,
        }
        print(json.dumps(error_response), flush=True)
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": None,
        }
        print(json.dumps(error_response), flush=True)
'
