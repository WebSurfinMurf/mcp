#!/usr/bin/env python3
import json
import sys

# Read initialization request
init_request = '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"1.0.0","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1}'
request = json.loads(init_request)

# Check the structure
print("Request structure:", file=sys.stderr)
print(f"  Method: {request.get('method')}", file=sys.stderr)
print(f"  Params: {request.get('params')}", file=sys.stderr)

# Check params structure
params = request.get('params', {})
print(f"  Protocol Version: {params.get('protocolVersion')}", file=sys.stderr)
print(f"  Capabilities type: {type(params.get('capabilities'))}", file=sys.stderr)
print(f"  Capabilities: {params.get('capabilities')}", file=sys.stderr)
print(f"  ClientInfo: {params.get('clientInfo')}", file=sys.stderr)

# Test MCP import
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    import mcp
    # Try to get version info
    try:
        print(f"MCP module: {mcp}", file=sys.stderr)
    except:
        pass
    
    # Create a minimal server
    server = Server("test-server")
    print("Server created successfully", file=sys.stderr)
    
    # Check what the server expects
    print(f"Server name: {server.name}", file=sys.stderr)
    
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)