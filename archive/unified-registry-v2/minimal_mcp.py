#!/usr/bin/env python3
import sys
import json
import time

# Log to file to verify we're being called
with open("/tmp/minimal_mcp.log", "a") as f:
    f.write(f"--- Service Started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")

for line in sys.stdin:
    # Log the raw request
    with open("/tmp/minimal_mcp.log", "a") as f:
        f.write(f"REQUEST: {line.strip()}\n")

    try:
        req = json.loads(line)
    except json.JSONDecodeError as e:
        with open("/tmp/minimal_mcp.log", "a") as f:
            f.write(f"JSON ERROR: {e}\n")
        continue
    
    response = {}

    if req.get("method") == "initialize":
        response = {
            "jsonrpc": "2.0", 
            "result": {
                "protocolVersion": "2024-11-05", 
                "serverInfo": {
                    "name": "minimal-echo",
                    "version": "1.0.0"
                }
            }, 
            "id": req.get("id")
        }
    elif req.get("method") == "tools/list":
        response = {
            "jsonrpc": "2.0", 
            "result": {
                "tools": [{
                    "name": "echo", 
                    "description": "Echo test tool", 
                    "inputSchema": {
                        "type": "object", 
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Message to echo back"
                            }
                        },
                        "required": ["message"]
                    }
                }]
            }, 
            "id": req.get("id")
        }
    elif req.get("method") == "tools/call":
        params = req.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "echo":
            msg = arguments.get("message", "default message")
            response = {
                "jsonrpc": "2.0", 
                "result": {
                    "content": [{
                        "type": "text", 
                        "text": f"Echo reply: {msg}"
                    }]
                }, 
                "id": req.get("id")
            }
        else:
            response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                },
                "id": req.get("id")
            }
    else:
        # Unknown method
        response = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": f"Method not found: {req.get('method')}"
            },
            "id": req.get("id")
        }
    
    # Log the response
    with open("/tmp/minimal_mcp.log", "a") as f:
        f.write(f"RESPONSE: {json.dumps(response)}\n")

    # Send response
    print(json.dumps(response), flush=True)
    
    # CRITICAL: Keep process alive briefly after responding
    # This tests if the issue is a race condition
    time.sleep(0.1)

# Log when stdin closes
with open("/tmp/minimal_mcp.log", "a") as f:
    f.write("--- Service Ended ---\n")