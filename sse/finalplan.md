# MCP SSE-Only Architecture - Final Implementation Plan

**Project**: MCP Server-Sent Events (SSE) Services  
**Location**: `/home/administrator/projects/mcp/sse/`  
**Date**: 2025-09-10  
**Purpose**: Streamlined SSE-only MCP services for web integration (LiteLLM, Open WebUI)

## Executive Summary

This plan outlines a complete refactoring of the MCP (Model Context Protocol) architecture to focus exclusively on SSE (Server-Sent Events) mode, eliminating stdio complexity. All services will be containerized, network-isolated, and exposed via consistent SSE endpoints for seamless integration with web-based AI platforms.

## Core Design Principles

1. **SSE-Only**: No stdio mode, no dual-mode complexity
2. **Container-First**: All services run in Docker containers
3. **Network Isolation**: Services isolated on `litellm-net` 
4. **Consistent Naming**: Simple names like `mcp-postgres`, `mcp-fetch`
5. **Protocol Compliance**: MCP 2025-06-18 specification with output schemas and enhanced security
6. **Auto-Discovery**: Services self-register capabilities
7. **Stateless Design**: No session management required
8. **Secure Secrets**: Environment variables stored in `/home/administrator/secrets/sse.env`

## Architecture Overview

```
┌──────────────────────────────────────────┐
│          Web Clients (LiteLLM)           │
└─────────────────┬────────────────────────┘
                  │ HTTP/SSE
                  ▼
      ┌──────────────────────┐
      │   Docker Network:     │
      │    litellm-net        │
      └──────────────────────┘
                  │
    ┌─────────────┴──────────────┐
    │                            │
┌───▼────┐  ┌────▼────┐  ┌─────▼─────┐
│  mcp-  │  │  mcp-   │  │   mcp-    │
│postgres│  │  fetch  │  │filesystem │
│  :8001 │  │  :8002  │  │   :8003   │
└────────┘  └─────────┘  └───────────┘
```

## Directory Structure

```
/home/administrator/projects/mcp/sse/
├── finalplan.md           # This document
├── README.md              # Quick start guide
├── docker-compose.yml     # Orchestration for all services
├── Dockerfile.base        # Base image with common dependencies
├── deploy.sh              # Master deployment script
├── .gitignore             # Excludes secrets and local files
├── config/
│   ├── services.yaml      # Service registry and ports
│   └── networks.yaml      # Network configuration
├── core/
│   ├── __init__.py
│   ├── mcp_sse.py        # Base SSE server class
│   ├── models.py         # Pydantic models
│   ├── protocol.py       # MCP protocol implementation
│   └── utils.py          # Shared utilities
├── services/
│   ├── postgres/
│   │   ├── Dockerfile
│   │   ├── service.py    # PostgreSQL MCP service
│   │   ├── models.py     # Service-specific models
│   │   └── requirements.txt
│   ├── fetch/
│   │   ├── Dockerfile
│   │   ├── service.py    # HTTP fetch service
│   │   ├── models.py
│   │   └── requirements.txt
│   ├── filesystem/
│   │   ├── Dockerfile
│   │   ├── service.py    # File operations service
│   │   ├── models.py
│   │   └── requirements.txt
│   └── [future services...]
├── scripts/
│   ├── test_service.sh    # Test individual service
│   ├── health_check.sh    # Check all services
│   └── cleanup.sh         # Remove all containers
└── docs/
    ├── API.md             # API documentation
    ├── SERVICES.md        # Service catalog
    └── INTEGRATION.md     # Integration guide
```

## Service Specifications

### 1. PostgreSQL Service (`mcp-postgres`)
- **Port**: 8001
- **Container Name**: `mcp-postgres`
- **Tools**:
  - `list_databases` - List all databases
  - `execute_sql` - Execute SQL queries
  - `list_tables` - List tables in database
  - `table_info` - Get table details
  - `query_stats` - Performance statistics

### 2. Fetch Service (`mcp-fetch`)
- **Port**: 8002
- **Container Name**: `mcp-fetch`
- **Tools**:
  - `fetch` - HTTP/HTTPS requests with markdown conversion

### 3. Filesystem Service (`mcp-filesystem`)
- **Port**: 8003
- **Container Name**: `mcp-filesystem`
- **Tools**:
  - `read_file` - Read file contents
  - `write_file` - Write to files
  - `list_directory` - List directory contents
  - `create_directory` - Create directories

### 4. GitHub Service (`mcp-github`)
- **Port**: 8004
- **Container Name**: `mcp-github`
- **Tools**:
  - `search_repositories` - Search GitHub repos
  - `get_repository` - Get repo details
  - `create_issue` - Create GitHub issues

### 5. Monitoring Service (`mcp-monitoring`)
- **Port**: 8005
- **Container Name**: `mcp-monitoring`
- **Tools**:
  - `get_container_logs` - Docker logs
  - `search_logs` - Search Loki logs
  - `get_system_metrics` - System metrics

## Core Implementation Details

### Base SSE Server Class (`core/mcp_sse.py`)

```python
import asyncio
import json
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

class MCPSSEServer:
    """Base class for MCP SSE services"""
    
    def __init__(self, name: str, version: str = "1.0.0", port: int = 8000):
        self.name = name
        self.version = version
        self.port = port
        self.app = FastAPI(title=f"MCP {name} Service")
        self.tools: Dict[str, callable] = {}
        self.protocol_version = "2024-11-05"
        self._setup_routes()
    
    def register_tool(self, name: str, handler: callable, schema: BaseModel, description: str):
        """Register a tool with the service"""
        self.tools[name] = {
            "handler": handler,
            "schema": schema,  # CRITICAL for validation and discovery
            "description": description
        }
    
    def get_endpoints(self) -> Dict:
        """Generate the endpoint capabilities structure."""
        tool_list = []
        for name, tool_data in self.tools.items():
            tool_list.append({
                "name": f"tools/{name}",
                "description": tool_data["description"],
                "inputSchema": tool_data["schema"].schema()  # Generate JSON schema from Pydantic model
            })
        return {"endpoints": tool_list}
    
    async def sse_stream(self, request: Request):
        """Generate SSE stream for client connections"""
        async def generate():
            try:
                # Send connection event
                yield f"event: connection\n"
                yield f"data: {json.dumps(self.get_service_info())}\n\n"
                
                # Send endpoint capabilities with schemas
                yield f"event: endpoint\n"
                yield f"data: {json.dumps(self.get_endpoints())}\n\n"
            
            # Keep connection alive
            while True:
                if await request.is_disconnected():
                    break
                await asyncio.sleep(30)
                yield f"event: ping\n"
                yield f"data: {json.dumps({'timestamp': datetime.now().isoformat()})}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    
    def run(self):
        """Start the SSE server"""
        uvicorn.run(self.app, host="0.0.0.0", port=self.port)
```

### Deployment Script (`deploy.sh`)

```bash
#!/bin/bash
# Master deployment script for MCP SSE services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Load environment variables from secure location
if [ -f /home/administrator/projects/secrets/sse.env ]; then
    export $(cat /home/administrator/projects/secrets/sse.env | xargs)
fi

# Commands
case "$1" in
    up)
        echo -e "${GREEN}Starting all MCP SSE services...${NC}"
        docker-compose up -d --build
        ./scripts/health_check.sh
        ;;
    
    down)
        echo -e "${YELLOW}Stopping all MCP SSE services...${NC}"
        docker-compose down
        ;;
    
    restart)
        $0 down
        $0 up
        ;;
    
    status)
        docker-compose ps
        ;;
    
    logs)
        SERVICE=${2:-}
        if [ -z "$SERVICE" ]; then
            docker-compose logs --tail=50 -f
        else
            docker-compose logs --tail=50 -f mcp-$SERVICE
        fi
        ;;
    
    test)
        SERVICE=${2:-postgres}
        ./scripts/test_service.sh $SERVICE
        ;;
    
    clean)
        echo -e "${RED}Removing all MCP containers and volumes...${NC}"
        docker-compose down -v
        docker system prune -f
        ;;
    
    *)
        echo "Usage: $0 {up|down|restart|status|logs|test|clean} [service]"
        exit 1
        ;;
esac
```

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  mcp-postgres:
    build:
      context: .
      dockerfile: services/postgres/Dockerfile
    container_name: mcp-postgres
    env_file:
      - /home/administrator/projects/secrets/sse.env
    environment:
      - SERVICE_PORT=8001
    ports:
      - "127.0.0.1:8001:8001"
    networks:
      - litellm-net
      - postgres-net
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  mcp-fetch:
    build:
      context: .
      dockerfile: services/fetch/Dockerfile
    container_name: mcp-fetch
    env_file:
      - /home/administrator/projects/secrets/sse.env
    environment:
      - SERVICE_PORT=8002
    ports:
      - "127.0.0.1:8002:8002"
    networks:
      - litellm-net
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  mcp-filesystem:
    build:
      context: .
      dockerfile: services/filesystem/Dockerfile
    container_name: mcp-filesystem
    env_file:
      - /home/administrator/projects/secrets/sse.env
    environment:
      - SERVICE_PORT=8003
      - ALLOWED_PATHS=/workspace,/shared
    volumes:
      - /home/administrator/workspace:/workspace:ro
      - /home/administrator/mcp-shared:/shared:rw
    ports:
      - "127.0.0.1:8003:8003"
    networks:
      - litellm-net
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  litellm-net:
    external: true
  postgres-net:
    external: true
```

## Protocol Implementation

### SSE Event Types
1. **connection** - Initial handshake with service info
2. **endpoint** - Service capabilities and tools
3. **tool_call** - Tool execution request
4. **tool_result** - Tool execution response
5. **error** - Error notifications
6. **ping** - Keep-alive messages

### RPC Endpoint (`/rpc`)
- POST endpoint for synchronous tool execution
- Request format:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute_sql",
    "arguments": {
      "query": "SELECT * FROM users"
    }
  },
  "id": 1
}
```

### Health Check (`/health`)
- GET endpoint returning service status
- Response:
```json
{
  "status": "healthy",
  "service": "postgres",
  "version": "1.0.0",
  "uptime": 3600,
  "tools_count": 5
}
```

## Migration Strategy

### Phase 1: Core Services (Week 1)
1. Implement base SSE server class
2. Deploy PostgreSQL service
3. Deploy Fetch service
4. Deploy Filesystem service
5. Test with LiteLLM integration

### Phase 2: Extended Services (Week 2)
1. Deploy GitHub service
2. Deploy Monitoring service
3. Deploy TimescaleDB service
4. Deploy n8n integration service

### Phase 3: Advanced Services (Week 3)
1. Deploy Playwright service
2. Deploy Memory/Vector service
3. Deploy OpenRouter integration
4. Performance optimization

## Testing Strategy

### Unit Tests
- Test each tool handler independently
- Validate input/output schemas
- Error handling scenarios

### Integration Tests
- SSE connection establishment
- RPC endpoint functionality
- Cross-service communication
- Network connectivity

### End-to-End Tests
- LiteLLM integration
- Open WebUI integration
- Multi-service workflows

## Security Considerations

1. **Network Isolation**: Services only on `litellm-net`
2. **No External Ports**: Bind to 127.0.0.1 only
3. **Input Validation**: Pydantic models for all inputs
4. **SQL Injection Prevention**: Parameterized queries
5. **File Access Control**: Restricted filesystem paths
6. **Rate Limiting**: Built-in request throttling
7. **Authentication Ready**: Can add JWT/OAuth2 later
8. **Secure Secrets Management**: All sensitive environment variables stored in `/home/administrator/projects/secrets/sse.env`

### Environment Variables Management

All sensitive configuration is stored in `/home/administrator/projects/secrets/sse.env`, which is a secure location on the system. This file is never committed to version control.

**Example `/home/administrator/projects/secrets/sse.env`:**
```bash
# Database Configuration
DATABASE_URL=postgresql://admin:Pass123qp@postgres:5432/postgres

# API Keys
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxx

# Service Configuration
LOG_LEVEL=INFO
MAX_CONNECTIONS=10
```

**Docker Compose Integration:**
```yaml
services:
  mcp-postgres:
    env_file:
      - /home/administrator/projects/secrets/sse.env  # Load all secrets
    environment:
      - SERVICE_PORT=8001  # Non-sensitive config can stay here
```

## Performance Optimizations

1. **Connection Pooling**: Reuse database connections
2. **Async Operations**: Non-blocking I/O throughout
3. **Response Streaming**: SSE for real-time updates
4. **Docker Layer Caching**: Optimized Dockerfiles
5. **Health Checks**: Automatic container recovery
6. **Resource Limits**: Memory/CPU constraints

## Monitoring & Observability

1. **Health Endpoints**: `/health` on each service
2. **Structured Logging**: JSON logs to stdout
3. **Metrics Collection**: Prometheus-compatible
4. **Distributed Tracing**: OpenTelemetry ready
5. **Error Tracking**: Sentry integration ready

## Success Metrics

1. **Response Time**: < 100ms for all operations
2. **Uptime**: 99.9% availability
3. **Integration Success**: Works with LiteLLM/Open WebUI
4. **Developer Experience**: Single command deployment
5. **Maintenance**: Zero-downtime updates

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Service Discovery | Consistent naming convention |
| Network Issues | Health checks and auto-restart |
| Protocol Changes | Versioned API endpoints |
| Resource Exhaustion | Container limits and monitoring |
| Integration Failures | Comprehensive error messages |

## Future Enhancements

1. **Service Mesh**: Istio/Linkerd for advanced networking
2. **API Gateway**: Kong/Traefik for unified entry
3. **Service Registry**: Consul for dynamic discovery
4. **Secrets Management**: Vault integration
5. **Multi-Region**: Geo-distributed deployment
6. **WebSocket Support**: Bidirectional communication
7. **GraphQL Interface**: Alternative query interface

## Implementation Timeline

### Day 1-2: Foundation
- Set up directory structure ✓
- Create base SSE server class with corrected `register_tool` method
- Implement protocol handlers with proper schema validation
- Set up Docker base image
- Create `/home/administrator/projects/secrets/sse.env` template

### Day 3-4: Core Services
- Port PostgreSQL service
- Port Fetch service
- Create Filesystem service
- Write deployment scripts

### Day 5-6: Testing & Integration
- Create test suite
- LiteLLM integration testing
- Documentation
- Performance testing

### Day 7: Launch
- Final testing
- Deploy to production
- Monitor and iterate

## Validation from AI Review

This plan has been validated by external AI review with the following key points:

1. **Architectural Superiority**: The SSE-only approach is confirmed as vastly simpler and more robust than dual-mode
2. **Production-Ready Design**: The container-first approach with health checks creates a self-healing system
3. **Excellent Developer Experience**: Simple `deploy.sh` interface abstracts complexity
4. **Security Best Practices**: Proper secrets management via `/home/administrator/secrets/sse.env`

### Critical Implementation Notes

1. **Prioritize Core Framework**: Build `Dockerfile.base` and `mcp_sse.py` base class first
2. **Schema Validation**: The `register_tool` method must include Pydantic schema for automatic validation
3. **Error Handling**: Add global exception handler in FastAPI to wrap errors in MCP SSE format
4. **Secrets Management**: Never commit secrets; always use the secure env file location

## Conclusion

This SSE-only architecture eliminates the complexity of dual-mode operation while providing a robust, scalable foundation for MCP services. The focus on containerization, consistent interfaces, and web-native protocols ensures seamless integration with modern AI platforms.

The plan has been **validated and is ready for implementation**.

**Key Benefits:**
- Simplified architecture (no stdio complexity)
- Consistent service interfaces
- Easy integration with web platforms
- Scalable and maintainable
- Production-ready from day one

**Next Steps:**
1. Review and approve this plan
2. Begin implementation of base classes
3. Port existing services to new architecture
4. Deploy and test with LiteLLM
5. Document and iterate

---
*This plan is ready for review and feedback before implementation begins.*