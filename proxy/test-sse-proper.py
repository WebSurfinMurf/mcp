#!/usr/bin/env python3
import requests
import json
import sseclient

print("Testing MCP SSE endpoints...")

# Test filesystem
url = "http://localhost:8585/servers/filesystem/sse"
headers = {'Accept': 'text/event-stream'}

print("\n1. Filesystem server:")
try:
    response = requests.get(url, headers=headers, stream=True, timeout=2)
    client = sseclient.SSEClient(response)
    
    # Get the endpoint from first event
    for event in client.events():
        if event.event == 'endpoint':
            endpoint = event.data
            print(f"   Endpoint: {endpoint}")
            
            # Send tools/list request
            messages_url = f"http://localhost:8585{endpoint}"
            tool_request = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 1
            }
            
            # Post the request and get SSE response
            resp = requests.post(messages_url, json=tool_request, headers=headers, stream=True)
            sse_client = sseclient.SSEClient(resp)
            
            for msg_event in sse_client.events():
                if msg_event.data:
                    try:
                        data = json.loads(msg_event.data)
                        if 'result' in data and 'tools' in data['result']:
                            tools = data['result']['tools']
                            print(f"   ✓ {len(tools)} tools available")
                            for tool in tools[:3]:
                                print(f"     - {tool['name']}")
                            break
                    except:
                        pass
            break
            
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test monitoring
print("\n2. Monitoring server:")
try:
    url = "http://localhost:8585/servers/monitoring/sse"
    response = requests.get(url, headers=headers, stream=True, timeout=2)
    client = sseclient.SSEClient(response)
    
    for event in client.events():
        if event.event == 'endpoint':
            endpoint = event.data
            print(f"   Endpoint: {endpoint}")
            
            messages_url = f"http://localhost:8585{endpoint}"
            tool_request = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 1
            }
            
            resp = requests.post(messages_url, json=tool_request, headers=headers, stream=True)
            sse_client = sseclient.SSEClient(resp)
            
            for msg_event in sse_client.events():
                if msg_event.data:
                    try:
                        data = json.loads(msg_event.data)
                        if 'result' in data and 'tools' in data['result']:
                            tools = data['result']['tools']
                            print(f"   ✓ {len(tools)} tools available")
                            for tool in tools[:3]:
                                print(f"     - {tool['name']}")
                            break
                    except:
                        pass
            break
            
except Exception as e:
    print(f"   ✗ Error: {e}")
