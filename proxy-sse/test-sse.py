#!/usr/bin/env python3
import requests
import json

print("Testing MCP SSE endpoints...")

# Test basic connectivity
try:
    # Try to connect to the proxy
    response = requests.get("http://localhost:8585/", timeout=2)
    print(f"Root endpoint status: {response.status_code}")
except Exception as e:
    print(f"Root endpoint error: {e}")

# Test SSE endpoint
try:
    headers = {'Accept': 'text/event-stream'}
    response = requests.get("http://localhost:8585/servers/filesystem/sse", 
                           headers=headers, stream=True, timeout=2)
    print(f"SSE endpoint status: {response.status_code}")
    
    # Try to read some data
    for line in response.iter_lines():
        if line:
            print(f"Received: {line.decode('utf-8')}")
            break
except Exception as e:
    print(f"SSE endpoint error: {e}")

# Test if we can list servers
try:
    response = requests.get("http://localhost:8585/servers", timeout=2)
    print(f"Servers list status: {response.status_code}")
    if response.status_code == 200:
        print(f"Servers: {response.text}")
except Exception as e:
    print(f"Servers list error: {e}")