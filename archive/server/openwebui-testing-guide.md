# MCP Server Testing Guide with Open WebUI

## 🎯 **Access Information**
- **MCP Server**: http://mcp.linuxserver.lan
- **Open WebUI**: http://localhost:8000
- **API Documentation**: http://mcp.linuxserver.lan/docs

## 🔧 **Setup Instructions**

### Method 1: Function Calling Integration
Open WebUI supports function calling. You can configure it to call the MCP server tools directly.

1. **Access Open WebUI**: http://localhost:8000
2. **Go to Settings** → **Functions**
3. **Add Custom Function** with these examples:

#### Database Query Function
```python
"""
title: PostgreSQL Query Tool
author: MCP Server Integration
version: 1.0.0
"""

import requests

def postgres_query(query: str, database: str = None) -> str:
    """
    Execute a read-only PostgreSQL query via MCP server

    Args:
        query: SQL SELECT query to execute
        database: Database name (optional)

    Returns:
        Query results in JSON format
    """
    try:
        response = requests.post(
            "http://mcp.linuxserver.lan/tools/postgres_query",
            json={"input": {"query": query, "database": database}},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return f"Query executed successfully:\n\nResults: {result['result']}"
    except Exception as e:
        return f"Error executing query: {str(e)}"
```

#### System Monitoring Function
```python
"""
title: System Metrics Tool
author: MCP Server Integration
version: 1.0.0
"""

import requests

def get_system_metrics(charts: list = None) -> str:
    """
    Get system metrics from Netdata via MCP server

    Args:
        charts: List of metric charts to retrieve (optional)

    Returns:
        System metrics data
    """
    try:
        payload = {"input": {}}
        if charts:
            payload["input"]["charts"] = charts

        response = requests.post(
            "http://mcp.linuxserver.lan/tools/get_system_metrics",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return f"System metrics retrieved:\n\n{result['result']}"
    except Exception as e:
        return f"Error getting metrics: {str(e)}"
```

#### Web Fetching Function
```python
"""
title: Web Content Fetcher
author: MCP Server Integration
version: 1.0.0
"""

import requests

def fetch_web_content(url: str) -> str:
    """
    Fetch web content and convert to markdown via MCP server

    Args:
        url: URL to fetch content from

    Returns:
        Web content converted to markdown
    """
    try:
        response = requests.post(
            "http://mcp.linuxserver.lan/tools/fetch_web_content",
            json={"input": {"url": url}},
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        return f"Content fetched from {url}:\n\n{result['result']}"
    except Exception as e:
        return f"Error fetching content: {str(e)}"
```

### Method 2: Direct API Testing

#### Test Database Tools
```bash
# List databases
curl -X POST http://mcp.linuxserver.lan/tools/postgres_list_databases \
  -H "Content-Type: application/json" \
  -d '{"input": {}}'

# Execute query
curl -X POST http://mcp.linuxserver.lan/tools/postgres_query \
  -H "Content-Type: application/json" \
  -d '{"input": {"query": "SELECT version();"}}'

# List tables
curl -X POST http://mcp.linuxserver.lan/tools/postgres_list_tables \
  -H "Content-Type: application/json" \
  -d '{"input": {"schema": "public"}}'
```

#### Test Storage Tools
```bash
# List MinIO objects
curl -X POST http://mcp.linuxserver.lan/tools/minio_list_objects \
  -H "Content-Type: application/json" \
  -d '{"input": {"bucket": "default-bucket", "prefix": ""}}'

# Get object content
curl -X POST http://mcp.linuxserver.lan/tools/minio_get_object \
  -H "Content-Type: application/json" \
  -d '{"input": {"bucket": "default-bucket", "object_name": "test.txt"}}'
```

#### Test Monitoring Tools
```bash
# Search logs
curl -X POST http://mcp.linuxserver.lan/tools/search_logs \
  -H "Content-Type: application/json" \
  -d '{"input": {"query": "{container=\"postgres\"}", "hours": 1, "limit": 10}}'

# Get system metrics
curl -X POST http://mcp.linuxserver.lan/tools/get_system_metrics \
  -H "Content-Type: application/json" \
  -d '{"input": {"charts": ["system.cpu", "system.ram"]}}'
```

#### Test Web & Filesystem Tools
```bash
# Fetch web content
curl -X POST http://mcp.linuxserver.lan/tools/fetch_web_content \
  -H "Content-Type: application/json" \
  -d '{"input": {"url": "https://httpbin.org/json"}}'

# List directory
curl -X POST http://mcp.linuxserver.lan/tools/list_directory \
  -H "Content-Type: application/json" \
  -d '{"input": {"path": "/tmp"}}'

# Read file
curl -X POST http://mcp.linuxserver.lan/tools/read_file \
  -H "Content-Type: application/json" \
  -d '{"input": {"path": "/etc/hostname"}}'
```

## 🎨 **Open WebUI Chat Examples**

Once functions are configured, you can use natural language in Open WebUI:

### Database Queries
- "Show me all databases in PostgreSQL"
- "Query the users table and show me the first 5 records"
- "What's the PostgreSQL version?"

### System Monitoring
- "Show me current CPU and memory usage"
- "Search for error logs in the last hour"
- "What containers are currently running?"

### Web Content
- "Fetch the content from https://example.com and summarize it"
- "Get the latest news from a tech website"

### File Operations
- "List files in the /tmp directory"
- "Read the content of /etc/hostname"
- "Show me the directory structure of /var/log"

## 🔍 **Interactive API Documentation**

Visit http://mcp.linuxserver.lan/docs for complete interactive API documentation with:
- Tool schemas and parameters
- Example requests and responses
- Live API testing interface
- LangChain agent endpoint (`/agent/invoke`)

## ⚡ **Performance Notes**

- **Internal Access**: ~1-5ms latency (container-to-container)
- **Security**: Read-only database operations, path-restricted file access
- **Concurrent Users**: Supports multiple simultaneous requests
- **Tool Categories**: Database, Storage, Monitoring, Web, Filesystem

## 🐛 **Troubleshooting**

### Connection Issues
```bash
# Test MCP server health
curl -s http://mcp.linuxserver.lan/health

# Check container status
docker ps | grep mcp-server

# View container logs
docker logs mcp-server --tail 20
```

### Function Integration Issues
- Ensure Open WebUI can reach `mcp.linuxserver.lan`
- Check function syntax in Open WebUI settings
- Verify JSON payload structure in API docs
- Test tools individually via curl first

---
*Created: 2025-09-14*
*Purpose: Enable comprehensive MCP server testing via Open WebUI*
*Tools: 10 integrated tools across 5 categories*