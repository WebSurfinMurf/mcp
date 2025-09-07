#!/usr/bin/env python3
import requests
import json

# Test filesystem SSE endpoint
url = "http://localhost:8585/servers/filesystem/sse"
headers = {'Accept': 'text/event-stream'}

print("Testing filesystem SSE endpoint...")
response = requests.get(url, headers=headers, stream=True, timeout=2)

if response.status_code == 200:
    # Get the endpoint URL from SSE
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                endpoint = line_str[6:]  # Remove 'data: ' prefix
                print(f"Got endpoint: {endpoint}")
                
                # Now send tools/list request
                messages_url = f"http://localhost:8585{endpoint}"
                tool_request = {
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": 1
                }
                
                print(f"Sending tools/list to: {messages_url}")
                response = requests.post(messages_url, json=tool_request)
                if response.status_code == 200:
                    result = response.json()
                    tools = result.get('result', {}).get('tools', [])
                    print(f"✓ Filesystem has {len(tools)} tools:")
                    for tool in tools[:3]:  # Show first 3
                        print(f"  - {tool['name']}")
                else:
                    print(f"✗ Failed: {response.status_code}")
                break
else:
    print(f"✗ SSE connection failed: {response.status_code}")
