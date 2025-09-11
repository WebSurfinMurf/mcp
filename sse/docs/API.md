# MCP SSE Services API Documentation

## Overview

MCP SSE Services provide Server-Sent Events (SSE) endpoints for Model Context Protocol integration with web-based AI platforms like LiteLLM and Open WebUI.

## Base URL Structure

Each service runs on a different port:
- **PostgreSQL**: http://localhost:8001
- **Fetch**: http://localhost:8002  
- **Filesystem**: http://localhost:8003
- **GitHub**: http://localhost:8004
- **Monitoring**: http://localhost:8005

## Common Endpoints

All services implement these standard endpoints:

### GET /health
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "service": "postgres", 
  "version": "1.0.0",
  "uptime": 3600.5,
  "tools_count": 5
}
```

### GET /info  
Service information

**Response:**
```json
{
  "name": "postgres",
  "version": "1.0.0", 
  "protocol_version": "2024-11-05",
  "port": 8001,
  "uptime": 3600.5,
  "tools_count": 5
}
```

### GET /tools
List available tools

**Response:**
```json
{
  "tools": [
    {
      "name": "list_databases",
      "description": "List all databases",
      "inputSchema": {
        "type": "object",
        "properties": {
          "include_size": {"type": "boolean"}
        }
      }
    }
  ]
}
```

### POST /rpc
JSON-RPC endpoint for tool execution

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call", 
  "params": {
    "name": "list_databases",
    "arguments": {
      "include_size": true
    }
  },
  "id": 1
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text", 
        "text": "Database list: postgres, template1, template0"
      }
    ]
  }
}
```

### GET /sse
Server-Sent Events stream

**Headers:**
- `Accept: text/event-stream`

**Events:**
- `connection` - Initial connection with service info
- `endpoint` - Service capabilities  
- `ping` - Keep-alive messages

**Example:**
```
event: connection
data: {"service": "postgres", "version": "1.0.0"}

event: endpoint  
data: {"endpoints": [{"name": "list_databases", ...}]}

event: ping
data: {"timestamp": "2025-09-10T10:00:00Z"}
```

## Error Responses

### HTTP Errors
- `404` - Endpoint not found
- `500` - Internal server error

### JSON-RPC Errors
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32601,
    "message": "Method not found"
  },
  "id": 1
}
```

## Authentication

Currently no authentication required. Services are bound to localhost only for security.

## Rate Limiting

No rate limiting implemented. Services are designed for internal use only.