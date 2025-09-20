# MCP Server Internal Access Guide

## 🏠 **Internal Network Access Pattern**

### **Two Access Methods Available**

#### 1. **Internal Direct Access** (Recommended for Development Tools)
- **URL**: `http://mcp.linuxserver.lan` (via Traefik routing)
- **Alt URL**: `http://mcp-server:8000` (direct container access)
- **Authentication**: None required (internal network only)
- **Performance**: Fastest - no authentication overhead
- **Use cases**: Claude Code, VS Code extensions, CI/CD, local scripts

#### 2. **External Authenticated Access**
- **URL**: `https://mcp.ai-servicers.com`
- **Authentication**: Keycloak SSO (administrators + developers groups)
- **Performance**: Slight overhead for OAuth2 proxy
- **Use cases**: Remote developers, web browsers, external tools

## 🔧 **Connecting Internal Tools**

### **Claude Code MCP Configuration**

Add to your Claude Code MCP settings (`~/.config/claude/mcp_servers.json`):

```json
{
  "mcpServers": {
    "unified-tools": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "http://mcp.linuxserver.lan/tools/{TOOL_NAME}",
        "-H", "Content-Type: application/json",
        "-d", "{\"input\": {TOOL_INPUT}}"
      ]
    }
  }
}
```

**Or create a wrapper script** for easier Claude Code integration:

```bash
#!/bin/bash
# /home/administrator/scripts/mcp-tool-wrapper.sh

TOOL_NAME="$1"
shift
TOOL_ARGS="$@"

curl -s -X POST "http://mcp.linuxserver.lan/tools/$TOOL_NAME" \
  -H "Content-Type: application/json" \
  -d "{\"input\": $TOOL_ARGS}" | jq -r '.result'
```

### **VS Code Extensions**

#### **REST Client Extension**
Create `.vscode/mcp-requests.http`:
```http
### Health Check
GET http://mcp.linuxserver.lan/health

### List All Tools
GET http://mcp.linuxserver.lan/tools

### PostgreSQL Query
POST http://mcp.linuxserver.lan/tools/postgres_query
Content-Type: application/json

{
  "input": {
    "query": "SELECT version();"
  }
}

### Search Logs
POST http://mcp.linuxserver.lan/tools/search_logs
Content-Type: application/json

{
  "input": {
    "query": "{container=\"mcp-server\"}",
    "hours": 1,
    "limit": 50
  }
}

### System Metrics
POST http://mcp.linuxserver.lan/tools/get_system_metrics
Content-Type: application/json

{
  "input": {
    "charts": ["system.cpu", "system.ram"]
  }
}
```

### **Python Development Scripts**

```python
#!/usr/bin/env python3
# mcp_client.py - Internal MCP client for development

import requests
import json

class MCPClient:
    def __init__(self, base_url="http://mcp.linuxserver.lan"):
        self.base_url = base_url

    def health_check(self):
        """Check MCP server health"""
        response = requests.get(f"{self.base_url}/health")
        return response.json()

    def list_tools(self):
        """Get all available tools"""
        response = requests.get(f"{self.base_url}/tools")
        return response.json()

    def call_tool(self, tool_name, **kwargs):
        """Call any MCP tool with parameters"""
        payload = {"input": kwargs}
        response = requests.post(
            f"{self.base_url}/tools/{tool_name}",
            headers={"Content-Type": "application/json"},
            json=payload
        )
        return response.json()

# Usage examples
if __name__ == "__main__":
    client = MCPClient()

    # Health check
    print("Health:", client.health_check())

    # Database query
    result = client.call_tool(
        "postgres_query",
        query="SELECT datname FROM pg_database LIMIT 5;"
    )
    print("Databases:", result)

    # Log search
    logs = client.call_tool(
        "search_logs",
        query="{container=\"postgres\"}",
        hours=1,
        limit=10
    )
    print("Recent logs:", logs)
```

### **Node.js Development Scripts**

```javascript
// mcp-client.js - Internal MCP client for Node.js

const axios = require('axios');

class MCPClient {
    constructor(baseUrl = 'http://mcp.linuxserver.lan') {
        this.baseUrl = baseUrl;
        this.client = axios.create({ baseURL: baseUrl });
    }

    async healthCheck() {
        const response = await this.client.get('/health');
        return response.data;
    }

    async listTools() {
        const response = await this.client.get('/tools');
        return response.data;
    }

    async callTool(toolName, params = {}) {
        const response = await this.client.post(`/tools/${toolName}`, {
            input: params
        });
        return response.data;
    }
}

// Usage example
async function main() {
    const mcp = new MCPClient();

    try {
        // Health check
        const health = await mcp.healthCheck();
        console.log('Health:', health);

        // Query database
        const dbResult = await mcp.callTool('postgres_query', {
            query: 'SELECT version();'
        });
        console.log('Database version:', dbResult);

        // Get system metrics
        const metrics = await mcp.callTool('get_system_metrics', {
            charts: ['system.cpu', 'system.ram']
        });
        console.log('System metrics:', metrics);

    } catch (error) {
        console.error('Error:', error.message);
    }
}

// Run if called directly
if (require.main === module) {
    main();
}

module.exports = MCPClient;
```

## 🐳 **Docker Network Integration**

### **Connect Existing Containers to MCP Network**

```bash
# Connect any container to access MCP server directly
docker network connect mcp-internal-net <your-container-name>

# Example: Connect a development container
docker run -d --name dev-tools \
  --network mcp-internal-net \
  node:18-alpine \
  sh -c "npm install axios && node -e 'console.log(\"Dev container ready\")'"

# Test MCP access from dev container
docker exec dev-tools node -e "
const axios = require('axios');
axios.get('http://mcp-server:8000/health')
  .then(r => console.log('MCP Health:', r.data))
  .catch(e => console.log('Error:', e.message));
"
```

### **Add to Existing Docker Compose Services**

```yaml
# Add to any existing docker-compose.yml
services:
  your-app:
    # ... existing configuration ...
    networks:
      - mcp-internal-net  # Add this line

networks:
  mcp-internal-net:
    external: true  # Reference the MCP network
```

## 🚀 **Performance Benefits**

### **Internal Access (Direct)**
- **Latency**: ~1-5ms (container to container)
- **Throughput**: Full Docker network speed
- **Overhead**: None - direct HTTP calls
- **Reliability**: No external dependencies

### **External Access (OAuth2)**
- **Latency**: ~50-200ms (includes internet + auth)
- **Throughput**: Limited by internet connection
- **Overhead**: OAuth2 token validation on each request
- **Reliability**: Depends on internet + Keycloak availability

## 📊 **Usage Recommendations**

### **Use Internal Access For:**
- ✅ **Claude Code**: Direct tool integration
- ✅ **VS Code extensions**: Development debugging
- ✅ **CI/CD pipelines**: Automated testing and deployment
- ✅ **Local development scripts**: Quick database queries
- ✅ **Container-to-container communication**: Microservices
- ✅ **High-frequency operations**: Monitoring, health checks

### **Use External Access For:**
- 🌐 **Remote developers**: Working from home/coffee shops
- 🌐 **Web-based tools**: Browser-based development interfaces
- 🌐 **External integrations**: Third-party services
- 🌐 **Occasional access**: Ad-hoc queries and exploration
- 🌐 **Collaborative debugging**: Shared access across team

## 🔐 **Security Considerations**

### **Internal Network Security**
- **Network isolation**: Only containers on `mcp-internal-net` can access
- **No authentication needed**: Docker network provides security boundary
- **Tool-level security**: Individual tools still enforce safety (read-only DB, path restrictions)

### **Access Control**
```bash
# List containers with MCP access
docker network inspect mcp-internal-net

# Remove container access if needed
docker network disconnect mcp-internal-net <container-name>
```

## ✅ **Testing Internal Access**

```bash
# Test from host machine (should fail - no network access)
curl http://mcp-server:8000/health
# Expected: Connection refused or timeout

# Test from container on mcp-internal-net (should work)
docker run --rm --network mcp-internal-net curlimages/curl \
  curl -s http://mcp-server:8000/health
# Expected: {"status": "healthy", ...}

# Test tool functionality
docker run --rm --network mcp-internal-net curlimages/curl \
  curl -s -X POST http://mcp-server:8000/tools/postgres_query \
  -H "Content-Type: application/json" \
  -d '{"input": {"query": "SELECT 1;"}}'
```

---
*Created: 2025-09-14*
*Purpose: Enable high-performance internal access for development tools*
*Security: Docker network isolation + tool-level safety*