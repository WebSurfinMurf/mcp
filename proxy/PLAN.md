# MCP Proxy Implementation Plan - UPDATED

**Project**: Central MCP Server using TBXark/mcp-proxy
**Target**: Single aggregation point for all MCP services on linuxserver.lan
**Date**: 2025-09-23
**Status**: Production-ready with version pinning, CORS security, and MCPO integration

## Requirements Analysis

### Original Requirements from `/home/administrator/projects/mcp/requirements.md`

1. **Simplify deployment** - Stick to LAN access on `linuxserver.lan`
2. **Avoid LiteLLM integration** - Previous attempts failed multiple times
3. **Central MCP server** - Single connection point for all MCP services
4. **Multi-client access** - Support Claude Code CLI, Gemini CLI, ChatGPT Codex CLI, Open-WebUI, VS Code
5. **Docker containerization** - Each MCP runs in own container (acceptable wrapper approach)
6. **Community-supported tools** - Prioritize tools with material community support
7. **Local deployment** - All MCPs deployed in `projects/mcp/{services}` directories
8. **Multiple transport support** - stdio, HTTP, SSE registration methods

### How TBXark/mcp-proxy Supports Requirements

| Requirement | TBXark/mcp-proxy Support | Rating |
|-------------|-------------------------|--------|
| **Central MCP server** | ✅ Designed specifically for "aggregating multiple MCP resource servers through single HTTP server" | Perfect |
| **LAN access** | ✅ HTTP server accessible at `linuxserver.lan:9090` | Perfect |
| **Avoid LiteLLM** | ✅ Completely standalone, no LiteLLM dependency | Perfect |
| **Multi-client access** | ✅ Single HTTP endpoint, any MCP-compatible client can connect | Perfect |
| **Docker support** | ✅ Official Docker image `ghcr.io/tbxark/mcp-proxy:latest` | Perfect |
| **Community support** | ✅ 535 GitHub stars, active development, MIT license | Good |
| **Multiple transports** | ✅ Supports stdio, SSE, streamable-http client types | Perfect |
| **Local deployment** | ✅ Can proxy to local MCP services in individual directories | Perfect |

**Overall Alignment**: 🎯 **Perfect Match** - TBXark/mcp-proxy addresses all requirements directly

## 🔧 Critical Architecture Revision: SSE-First Approach

### Key Changes from User Feedback
Based on detailed analysis of TBXark/mcp-proxy documentation and best practices:

1. **Eliminate Docker CLI Complexity**: Avoid `docker exec` stdio transport which requires Docker socket mounting and CLI installation
2. **SSE-First Strategy**: Use Server-Sent Events (SSE) for containerized MCP services where possible
3. **Correct Config Schema**: Use `mcpProxy` + `mcpServers` structure as documented
4. **Built-in stdio Support**: Use proxy's internal `npx`/`uvx` for stdio-only services
5. **Proper Client Configuration**: Leverage official remote MCP support in Claude Code and VS Code

### The SSE Advantage
- **Security**: No Docker socket exposure required
- **Reliability**: Direct HTTP/SSE connections vs container exec
- **Simplicity**: Standard network protocols vs Docker API dependencies
- **Performance**: Lower overhead than exec-based stdio transport

## Architecture Overview

```
External Clients                Standard Proxy              Individual MCP Services
┌─────────────────┐             ┌─────────────────┐        ┌─────────────────────────────┐
│ Claude Code CLI │────────┐    │ TBXark          │        │ projects/mcp/postgres       │
│ (SSE URLs)      │        │    │ mcp-proxy       │   SSE  │ ├── crystaldba/postgres-mcp │
├─────────────────┤        │    │                 │────────│ └── SSE at :8686/sse        │
│ VS Code         │────────┼────│ Port: 9090      │        ├─────────────────────────────┤
│ (SSE URLs)      │        │    │                 │   stdio│ Built-in via npx/uvx:       │
├─────────────────┤        │    │ Per-service     │────────│ ├── mcp-server-fetch        │
│ Open-WebUI      │────────┤    │ endpoints:      │        │ └── mcp-server-filesystem   │
│ (HTTP)          │        │    │ /postgres/sse   │        ├─────────────────────────────┤
├─────────────────┤        │    │ /fetch/sse      │   SSE  │ projects/mcp/timescaledb    │
│ Other Clients   │────────┘    │ /filesystem/sse │────────│ ├── postgres-mcp (2nd inst) │
│ (SSE/HTTP)      │             └─────────────────┘        │ └── SSE at :8687/sse        │
└─────────────────┘                                        └─────────────────────────────┘
```

## Implementation Action Plan

### Phase 1: Core Infrastructure Setup (Day 1)

#### 1.1 Standard Proxy Deployment
```bash
# No custom build needed - use official image
cd /home/administrator/projects/mcp/proxy
docker-compose up -d mcp-proxy
```

#### 1.2 Network Configuration
```bash
# Create dedicated Docker network for MCP services
docker network create mcp-net --subnet=172.30.0.0/16
```

#### 1.3 Base Directory Structure
```
projects/mcp/proxy/
├── PLAN.md                     # This file
├── config/
│   └── config.json            # Central proxy configuration (correct schema)
├── docker-compose.yml         # Proxy deployment
├── scripts/
│   ├── deploy.sh              # Main deployment script
│   ├── health-check.sh        # Service health verification
│   └── add-mcp-service.sh     # Script to register new MCP services
├── docs/
│   ├── CLIENT-SETUP.md        # How to connect different clients
│   └── TROUBLESHOOTING.md     # Common issues and solutions
└── logs/                      # Proxy and service logs
```

#### 1.4 Standard Proxy Deployment
- Deploy official TBXark/mcp-proxy image
- Configure with correct `mcpProxy`/`mcpServers` schema
- Set up SSE server on port 9090
- Test built-in npx/uvx stdio support

### Phase 2: MCP Service Integration (Days 2-3)

#### 2.1 Priority MCP Services (SSE-First Strategy)
Based on community adoption and reliable transport methods:

1. **crystaldba/postgres-mcp** - Database operations (SSE transport)
2. **mcp-server-fetch** - Web content retrieval (stdio via npx)
3. **mcp-server-filesystem** - File operations (stdio via npx)
4. **postgres-mcp (TimescaleDB)** - Time-series data (SSE, second instance)
5. **playwright-mcp** - Browser automation (SSE if available)

#### 2.2 Service Deployment Patterns

**SSE Services (Containerized):**
```bash
projects/mcp/{service}/
├── docker-compose.yml         # SSE-enabled container
├── .env                       # Service environment variables
└── README.md                  # Service documentation
```

**stdio Services (Built-in):**
- Run directly inside proxy via `npx`/`uvx`
- No separate containers needed
- Configured in proxy's `config.json`

#### 2.3 Corrected Configuration Schema
Central proxy configuration uses proper `mcpProxy`/`mcpServers` structure:
```json
{
  "mcpProxy": {
    "baseURL": "http://linuxserver.lan:9090",
    "addr": ":9090",
    "name": "Central MCP Proxy",
    "type": "sse",
    "options": {
      "logEnabled": true,
      "authTokens": ["changeme-token"]
    }
  },
  "mcpServers": {
    "postgres": {
      "url": "http://mcp-postgres:8686/sse",
      "headers": {}
    },
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "/workspace"]
    }
  }
}
```

### Phase 3: Client Integration (Days 4-5)

#### 3.1 Claude Code CLI Setup (Remote MCP)
Configure multiple SSE URLs under same base host:
```json
{
  "mcpServers": {
    "postgres": {
      "type": "sse",
      "url": "http://linuxserver.lan:9090/postgres/sse",
      "headers": { "Authorization": "Bearer changeme-token" }
    },
    "fetch": {
      "type": "sse",
      "url": "http://linuxserver.lan:9090/fetch/sse",
      "headers": { "Authorization": "Bearer changeme-token" }
    },
    "filesystem": {
      "type": "sse",
      "url": "http://linuxserver.lan:9090/filesystem/sse",
      "headers": { "Authorization": "Bearer changeme-token" }
    }
  }
}
```

#### 3.2 Open-WebUI Integration (via MCPO)
Configure Open-WebUI to use MCP→OpenAPI proxy (MCPO):
1. Deploy MCPO instances pointing to each MCP SSE endpoint
2. Register MCPO OpenAPI endpoints in Open-WebUI
3. Test web-based tool access through OpenAPI layer

**Note**: Open-WebUI uses MCPO (MCP→OpenAPI proxy) rather than direct MCP integration for stability.

#### 3.3 VS Code Integration
- Set up MCP extension configuration
- Test remote connection from different machine
- Document connection parameters

#### 3.4 Additional CLI Tools
- Gemini CLI configuration
- ChatGPT Codex CLI setup (if available)
- Test tool compatibility across clients

### Phase 4: Production Hardening (Day 6)

#### 4.1 Security Configuration
- Network isolation with mcp-net
- Docker socket security considerations
- Log aggregation and monitoring

#### 4.2 Health Monitoring
- Service health checks
- Proxy status monitoring
- Integration with existing observability stack (Loki/Grafana)

#### 4.3 Backup and Recovery
- Configuration backup procedures
- Service restart automation
- Disaster recovery documentation

## Drop-in Ready Configuration Files

### Production Proxy Deployment (`docker-compose.yml`)
```yaml
version: "3.8"
services:
  mcp-proxy:
    image: ghcr.io/tbxark/mcp-proxy:v0.39.1  # Pin to specific release
    container_name: mcp-proxy
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./config:/config               # contains config.json
      - ./logs:/logs
      - /home/administrator/projects:/workspace:ro  # Read-only workspace for filesystem MCP
    command: ["-config", "/config/config.json"]
    networks:
      - mcp-net
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:9090/"]
      interval: 30s
      timeout: 5s
      retries: 3
    environment:
      - NODE_ENV=production

networks:
  mcp-net:
    external: true
```

### Production-Ready Proxy Configuration (`config/config.json`)
```json
{
  "mcpProxy": {
    "baseURL": "http://linuxserver.lan:9090",
    "addr": ":9090",
    "name": "Central MCP Proxy",
    "options": {
      "logEnabled": true,
      "panicIfInvalid": false,
      "authTokens": ["changeme-token"],
      "cors": {
        "origins": ["http://linuxserver.lan", "http://linuxserver.lan:*"]
      }
    }
  },
  "mcpServers": {
    "postgres": {
      "url": "http://mcp-postgres:8686/sse",
      "headers": { "X-Env": "prod" }
    },
    "timescaledb": {
      "url": "http://mcp-timescaledb:8687/sse",
      "headers": { "X-Env": "prod" }
    },
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "/workspace"]
    }
  }
}
```

### Individual MCP Service Templates

#### PostgreSQL MCP Service (`projects/mcp/postgres/docker-compose.yml`)
```yaml
version: "3.8"
services:
  mcp-postgres:
    image: crystaldba/postgres-mcp:1.0.0  # Pin to specific version
    container_name: mcp-postgres
    restart: unless-stopped
    environment:
      - DATABASE_URI=postgresql://admin:Pass123qp@postgres:5432/postgres
    command: ["postgres-mcp", "--transport", "sse", "--host", "0.0.0.0", "--port", "8686"]
    ports:
      - "48010:8686"                  # optional: only if you want to test from host
    networks:
      - mcp-net
      - postgres-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8686/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  mcp-net:
    external: true
  postgres-net:
    external: true
```

#### TimescaleDB MCP Service (`projects/mcp/timescaledb/docker-compose.yml`)
```yaml
version: "3.8"
services:
  mcp-timescaledb:
    image: crystaldba/postgres-mcp:1.0.0  # Pin to same version as postgres
    container_name: mcp-timescaledb
    restart: unless-stopped
    environment:
      - DATABASE_URI=postgresql://admin:TimescaleSecure2025@timescaledb:5433/timeseries
    command: ["postgres-mcp", "--transport", "sse", "--host", "0.0.0.0", "--port", "8687"]
    ports:
      - "48011:8687"                  # optional: testing access
    networks:
      - mcp-net
      - timescaledb-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8687/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  mcp-net:
    external: true
  timescaledb-net:
    external: true
```

**Note**: fetch and filesystem services run as stdio inside the proxy via npx/uvx - no separate containers needed.

**Production Tip**: TimescaleDB is PostgreSQL + extensions, so the same postgres-mcp image works perfectly for both services.

## Client Connection Examples

### Claude Code CLI Configuration (Remote MCP - Official Support)
```json
{
  "mcpServers": {
    "postgres": {
      "type": "sse",
      "url": "http://linuxserver.lan:9090/postgres/sse",
      "headers": { "Authorization": "Bearer changeme-token" }
    },
    "fetch": {
      "type": "sse",
      "url": "http://linuxserver.lan:9090/fetch/sse",
      "headers": { "Authorization": "Bearer changeme-token" }
    },
    "filesystem": {
      "type": "sse",
      "url": "http://linuxserver.lan:9090/filesystem/sse",
      "headers": { "Authorization": "Bearer changeme-token" }
    },
    "timescaledb": {
      "type": "sse",
      "url": "http://linuxserver.lan:9090/timescaledb/sse",
      "headers": { "Authorization": "Bearer changeme-token" }
    }
  }
}
```

### VS Code Extension Configuration
```json
{
  "mcp.servers": {
    "postgres": {
      "transport": "sse",
      "url": "http://linuxserver.lan:9090/postgres/sse",
      "headers": { "Authorization": "Bearer changeme-token" }
    },
    "fetch": {
      "transport": "sse",
      "url": "http://linuxserver.lan:9090/fetch/sse",
      "headers": { "Authorization": "Bearer changeme-token" }
    },
    "filesystem": {
      "transport": "sse",
      "url": "http://linuxserver.lan:9090/filesystem/sse",
      "headers": { "Authorization": "Bearer changeme-token" }
    },
    "timescaledb": {
      "transport": "sse",
      "url": "http://linuxserver.lan:9090/timescaledb/sse",
      "headers": { "Authorization": "Bearer changeme-token" }
    }
  }
}
```

## Testing and Validation Plan - Revised

### Manual SSE Testing (Production Smoke Tests)
Test SSE endpoints manually with curl:
```bash
# Test proxy root health check
curl -f http://linuxserver.lan:9090/

# Test postgres SSE endpoint (direct container)
curl -N -H 'Accept: text/event-stream' -H 'Authorization: Bearer changeme-token' \
  http://linuxserver.lan:9090/postgres/sse

# Test timescaledb SSE endpoint (second postgres instance)
curl -N -H 'Accept: text/event-stream' -H 'Authorization: Bearer changeme-token' \
  http://linuxserver.lan:9090/timescaledb/sse

# Test fetch SSE endpoint (stdio via proxy npx/uvx)
curl -N -H 'Accept: text/event-stream' -H 'Authorization: Bearer changeme-token' \
  http://linuxserver.lan:9090/fetch/sse

# Test filesystem SSE endpoint (stdio via proxy npx)
curl -N -H 'Accept: text/event-stream' -H 'Authorization: Bearer changeme-token' \
  http://linuxserver.lan:9090/filesystem/sse

# Test authentication failure (should return 401/403)
curl -N -H 'Accept: text/event-stream' \
  http://linuxserver.lan:9090/postgres/sse
```

### Functional Tests
1. **Proxy Health**: Verify proxy starts and responds on port 9090
2. **Service Discovery**: Confirm all MCP services discoverable via SSE
3. **Tool Execution**: Test tools from each backend service work correctly
4. **Multi-Client**: Verify concurrent access from different clients
5. **Authentication**: Test Bearer token requirement works correctly

### Integration Tests
1. **Database Operations**: Execute SQL queries through postgres SSE
2. **File Operations**: Read/write files through filesystem stdio
3. **Web Fetching**: Retrieve web content through fetch stdio
4. **Cross-Service**: Test workflows using multiple MCP services

### Security Validation
1. **Network Isolation**: Verify proper mcp-net segmentation
2. **Authentication**: Confirm Bearer token protection works
3. **LAN Only**: Test external access is properly blocked
4. **Container Security**: No Docker socket exposure needed

## Risk Assessment and Mitigation - Updated

### Technical Risks - Revised
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| SSE connection failure | Medium | Low | Standard HTTP/SSE protocols, well-tested |
| Built-in stdio failure | Medium | Low | Official mcp-proxy npx/uvx support |
| Proxy failure | High | Low | Health monitoring, auto-restart |
| Service incompatibility | Medium | Medium | Use documented community images |
| Network issues | Medium | Low | Standard Docker networking |
| Client compatibility | Low | Low | Official remote MCP support in clients |

### Security Considerations - Improved
| Concern | Assessment | Mitigation |
|---------|------------|------------|
| No Docker socket needed | Low | **Eliminated** - no socket exposure required |
| Bearer token auth | Low | Built-in authentication via authTokens |
| Network exposure | Low | Internal mcp-net only, no external exposure |
| Container isolation | Low | Standard Docker isolation, no special privileges |

## Success Metrics

### Technical Metrics
- **Uptime**: >99.5% proxy availability
- **Response Time**: <500ms for SSE connection establishment
- **Concurrent Users**: Support 10+ simultaneous connections
- **Service Coverage**: All planned MCP services operational via SSE
- **SSE Reliability**: 100% success rate for SSE transport

### User Experience Metrics
- **Setup Time**: New client connection in <5 minutes (simpler config)
- **Tool Discovery**: All tools visible from all clients via SSE
- **Error Rate**: <1% failed tool executions
- **Authentication**: Bearer token auth working correctly

## Next Steps - Production Implementation

1. **Deploy Pinned Proxy** - Use official mcp-proxy v0.39.1 with production config
2. **Configure SSE Services** - Deploy crystaldba/postgres-mcp:1.0.0 with SSE transport
3. **Test Built-in stdio** - Validate npx/uvx stdio services in proxy
4. **Expand Service Coverage** - Add TimescaleDB SSE service (port 8687)
5. **Client Integration** - Configure Claude Code and VS Code with per-service SSE URLs
6. **MCPO Setup** - Deploy MCP→OpenAPI proxy for Open-WebUI integration
7. **Production Validation** - Full testing with Bearer token authentication and CORS

---

**Implementation Owner**: Claude Code
**Review Status**: ✅ **Production-Ready Plan Approved** - Hardened SSE-first approach
**Estimated Timeline**: 3-4 days implementation + 1 day MCPO integration
**Dependencies**: Docker, existing postgres/timescaledb infrastructure
**Success Criteria**: Multiple SSE endpoints accessible from all target clients on linuxserver.lan

**Production Enhancements Applied**:
- ✅ Version pinning for all images (mcp-proxy:v0.39.1, postgres-mcp:1.0.0)
- ✅ CORS security with LAN-only origins
- ✅ panicIfInvalid: false for resilient proxy operation
- ✅ Health checks for all containerized services
- ✅ MCPO integration path for Open-WebUI
- ✅ Comprehensive SSE smoke testing procedures
- ✅ Tightened authentication with Bearer tokens
- ✅ Read-only workspace volume for filesystem MCP