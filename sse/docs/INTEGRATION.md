# MCP SSE Integration Guide

## Overview

This guide explains how to integrate MCP SSE services with various AI platforms and tools.

## LiteLLM Integration

### Configuration

Add MCP tools to LiteLLM configuration:

```yaml
# litellm_config.yaml
litellm_settings:
  tools:
    - name: "postgres_list_databases"
      endpoint: "http://localhost:8001/rpc"
      method: "POST"
      schema:
        type: "object"
        properties:
          include_size:
            type: "boolean"
            description: "Include database sizes"
    
    - name: "fetch_content"
      endpoint: "http://localhost:8002/rpc" 
      method: "POST"
      schema:
        type: "object"
        properties:
          url:
            type: "string"
            description: "URL to fetch"
```

### Usage Example

```python
import litellm

# Use MCP tool via LiteLLM
response = litellm.completion(
    model="gpt-4",
    messages=[{"role": "user", "content": "List all databases"}],
    tools=[
        {
            "type": "function",
            "function": {
                "name": "postgres_list_databases",
                "description": "List all databases",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "include_size": {"type": "boolean"}
                    }
                }
            }
        }
    ]
)
```

## Open WebUI Integration

Open WebUI integrates via LiteLLM. Configure LiteLLM as above, then Open WebUI will automatically discover the tools.

### Steps:
1. Configure LiteLLM with MCP endpoints
2. Restart LiteLLM service
3. Tools appear automatically in Open WebUI
4. Users can invoke tools in chat

## Claude Code Integration  

### Direct SSE Connection

Create Claude Code MCP server configuration:

```json
{
  "mcpServers": {
    "mcp-postgres": {
      "command": "curl",
      "args": ["-N", "-H", "Accept: text/event-stream", "http://localhost:8001/sse"],
      "env": {}
    }
  }
}
```

### Via HTTP Bridge

Create a simple bridge script for stdio mode compatibility:

```bash
#!/bin/bash
# mcp-sse-bridge.sh
SERVICE_URL="http://localhost:8001/rpc"

while IFS= read -r line; do
    response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$line" \
        "$SERVICE_URL")
    echo "$response"
done
```

## Custom Client Integration

### Python Client Example

```python
import asyncio
import json
import aiohttp

class MCPSSEClient:
    def __init__(self, base_url):
        self.base_url = base_url
        
    async def call_tool(self, tool_name, arguments=None):
        """Call an MCP tool via RPC endpoint"""
        url = f"{self.base_url}/rpc"
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            },
            "id": 1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                return await response.json()
    
    async def stream_events(self):
        """Stream SSE events"""
        url = f"{self.base_url}/sse"
        headers = {"Accept": "text/event-stream"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                async for line in response.content:
                    if line.startswith(b"data: "):
                        data = json.loads(line[6:])
                        yield data

# Usage
async def main():
    client = MCPSSEClient("http://localhost:8001")
    
    # Call a tool
    result = await client.call_tool("list_databases", {"include_size": True})
    print(result)
    
    # Stream events  
    async for event in client.stream_events():
        print(f"Event: {event}")

asyncio.run(main())
```

### JavaScript Client Example

```javascript
// MCP SSE Client for browsers/Node.js
class MCPSSEClient {
    constructor(baseURL) {
        this.baseURL = baseURL;
    }
    
    async callTool(toolName, arguments = {}) {
        const response = await fetch(`${this.baseURL}/rpc`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'tools/call',
                params: { name: toolName, arguments },
                id: 1
            })
        });
        return await response.json();
    }
    
    streamEvents(callback) {
        const eventSource = new EventSource(`${this.baseURL}/sse`);
        
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            callback(data);
        };
        
        return eventSource;
    }
}

// Usage
const client = new MCPSSEClient('http://localhost:8001');

// Call tool
client.callTool('list_databases', { include_size: true })
    .then(result => console.log(result));

// Stream events
const eventSource = client.streamEvents((data) => {
    console.log('Event:', data);
});
```

## Health Monitoring

### Service Health Check

```bash
#!/bin/bash
# check-mcp-health.sh

services=("postgres:8001" "fetch:8002" "filesystem:8003" "github:8004" "monitoring:8005")

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    
    if curl -s -f "http://localhost:$port/health" > /dev/null; then
        echo "✓ mcp-$name is healthy"
    else
        echo "✗ mcp-$name is unhealthy"
    fi
done
```

### Prometheus Monitoring

Add to Prometheus configuration:

```yaml
scrape_configs:
  - job_name: 'mcp-sse-services'
    static_configs:
      - targets: ['localhost:8001', 'localhost:8002', 'localhost:8003', 'localhost:8004', 'localhost:8005']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check if containers are running: `docker ps | grep mcp-`
   - Check if networks exist: `docker network ls`
   - Test health endpoints: `curl http://localhost:8001/health`

2. **SSE Stream Not Working**
   - Verify Accept header: `Accept: text/event-stream`
   - Check for proxy/firewall blocking
   - Test with curl: `curl -N -H "Accept: text/event-stream" http://localhost:8001/sse`

3. **Tool Execution Errors**
   - Check tool schemas: `curl http://localhost:8001/tools`
   - Validate input parameters
   - Check service logs: `docker logs mcp-postgres`

4. **Permission Denied (Filesystem Service)**
   - Check volume mounts in docker-compose.yml
   - Verify ALLOWED_PATHS environment variable
   - Check file permissions on host

### Debugging Commands

```bash
# Test all services
./deploy.sh test

# Check specific service
./scripts/test_service.sh postgres  

# View logs
./deploy.sh logs postgres

# Check container status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Test SSE endpoint
curl -N -H "Accept: text/event-stream" http://localhost:8001/sse

# Test RPC endpoint
curl -X POST http://localhost:8001/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

## Best Practices

1. **Always check health endpoints** before attempting tool calls
2. **Use connection pooling** for high-volume applications  
3. **Handle SSE disconnections** gracefully with reconnection logic
4. **Validate tool parameters** before sending requests
5. **Monitor service logs** for errors and performance issues
6. **Use environment variables** for service URLs in production
7. **Implement retries** for transient network errors

## Performance Considerations

- Services are designed for concurrent use
- Database connections are pooled automatically
- SSE streams are lightweight but maintain persistent connections
- RPC endpoints are stateless and scale horizontally
- File operations are limited by disk I/O
- Monitor memory usage for large file operations