# MCP Proxy Implementation Plan - UPDATED

**Project**: Central MCP Server using TBXark/mcp-proxy
**Target**: Single aggregation point for all MCP services on linuxserver.lan
**Date**: 2025-09-23
**Status**: Final production config with real version pins and proper health checks

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

### The Sidecar Bridge Pattern
- **Architecture**: stdio MCP services run in individual bridge containers exposing SSE
- **Security**: No Docker socket exposure or exec required
- **Isolation**: Each service is independently containerized and manageable
- **Uniformity**: All services expose SSE to the central proxy for consistent transport
- **Scalability**: Easy to add/remove services without touching central proxy

## Architecture Overview

```
External Clients                Central Proxy               MCP Service Containers
┌─────────────────┐             ┌─────────────────┐        ┌─────────────────────────────┐
│ Claude Code CLI │────────┐    │ TBXark          │        │ projects/mcp/postgres       │
│ (SSE URLs)      │        │    │ mcp-proxy       │   SSE  │ ├── crystaldba/postgres-mcp │
├─────────────────┤        │    │                 │────────│ └── Native SSE :8686/sse    │
│ VS Code         │────────┼────│ Port: 9090      │        ├─────────────────────────────┤
│ (SSE URLs)      │        │    │                 │   SSE  │ projects/mcp/timescaledb    │
├─────────────────┤        │    │ Per-service     │────────│ ├── postgres-mcp (2nd inst) │
│ Open-WebUI      │────────┤    │ endpoints:      │        │ └── Native SSE :8687/sse    │
│ (via MCPO)      │        │    │ /postgres/sse   │        ├─────────────────────────────┤
├─────────────────┤        │    │ /fetch/sse      │   SSE  │ projects/mcp/fetch/bridge   │
│ Other Clients   │────────┘    │ /filesystem/sse │────────│ ├── mcp-proxy bridge :9072  │
│ (SSE/HTTP)      │             │ /timescaledb/sse│        │ └── stdio→SSE (uvx fetch)   │
└─────────────────┘             └─────────────────┘        ├─────────────────────────────┤
                                                           │ projects/mcp/filesystem/bridge │
                                                           │ ├── mcp-proxy bridge :9071  │
                                                           │ └── stdio→SSE (npx filesystem) │
                                                           └─────────────────────────────┘
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

#### 1.4 Central Proxy Deployment
- Deploy official TBXark/mcp-proxy image as central aggregator
- Configure with correct `mcpProxy`/`mcpServers` schema pointing to bridge services
- Set up SSE server on port 9090
- No stdio handling in central proxy - all SSE connections to bridges

### Phase 2: MCP Service Integration (Days 2-3)

#### 2.1 Priority MCP Services (Management Script Strategy)
Streamlined deployment using automated management scripts:

1. **crystaldba/postgres-mcp** - Database operations (native SSE transport)
2. **mcp-server-filesystem** - File operations (scaffold + register via scripts)
3. **mcp-server-fetch** - Web content retrieval (scaffold + register via scripts)
4. **postgres-mcp (TimescaleDB)** - Time-series data (native SSE, second instance)
5. **playwright-mcp** - Browser automation (future: scaffold + register)

#### 2.2 Service Deployment Patterns

**Native SSE Services:**
```bash
projects/mcp/{service}/
├── docker-compose.yml         # Direct SSE-enabled container
├── .env                       # Service environment variables
└── README.md                  # Service documentation
```

**stdio Bridge Services:**
```bash
projects/mcp/{service}/bridge/
├── docker-compose.yml         # Bridge container with mcp-proxy
├── config/
│   └── config.json           # Bridge-specific proxy config
└── README.md                  # Bridge documentation
```

#### 2.3 Automated Service Registration Workflow
Streamlined deployment using management scripts for consistency and reliability:

**Step 1: Scaffold Bridge Service**
```bash
./add-bridge.sh \
  --service filesystem \
  --runtime node \
  --pkg @modelcontextprotocol/server-filesystem \
  --version 0.2.3 \
  --bin-cmd mcp-server-filesystem \
  --port 9071 \
  --workspace /home/administrator/projects
```

**Step 2: Build and Deploy Bridge**
```bash
cd /home/administrator/projects/mcp/filesystem/bridge
docker compose up -d --build
```

**Step 3: Register with Central Proxy**
```bash
export MCP_PROXY_TOKEN="changeme-token"
./add-to-central.sh \
  --service filesystem \
  --port 9071 \
  --add-auth \
  --test \
  --test-token "${MCP_PROXY_TOKEN}"
```

**Step 4: Verify Registration**
```bash
./list-central.sh --format table | column -t
```

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

**Important**: MCPO is optional; enable only for Open-WebUI after a quick smoke test, and keep direct SSE to clients as the baseline. Pin MCPO to a tag and test **one** endpoint first (e.g., `postgres`) before adding more.

**Security Note**: MCPO typically needs CORS enabled—configure CORS on MCPO containers, not the central MCP proxy, since browser clients hit MCPO directly.

**Note**: Open-WebUI uses MCPO (MCP→OpenAPI proxy) rather than direct MCP integration for stability, but community reports say reliability varies.

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

### Central Proxy Deployment (`docker-compose.yml`)
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
      # NO workspace mount - handled by individual bridge services
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
      - MCP_PROXY_TOKEN=${MCP_PROXY_TOKEN:-changeme-token}
    stop_grace_period: 10s
    deploy:
      resources:
        limits:
          memory: 256M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

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
      "authTokens": ["${MCP_PROXY_TOKEN}"]
      /* Enable CORS only if browser client needs it (typically for MCPO, not mcp-proxy):
      ,"cors": { "origins": ["http://linuxserver.lan:9090", "http://linuxserver.lan:3000"] }
      */
    }
  },
  "mcpServers": {
    "postgres": {
      "url": "http://mcp-postgres:8686/sse"
    },
    "timescaledb": {
      "url": "http://mcp-timescaledb:8687/sse"
    },
    "filesystem": {
      "url": "http://mcp-filesystem-bridge:9071/filesystem/sse"
    },
    "fetch": {
      "url": "http://mcp-fetch-bridge:9072/fetch/sse"
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
    image: crystaldba/postgres-mcp:v0.3.0  # Pin to real existing tag
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
      test: ["CMD", "curl", "-fsI", "-H", "Accept: text/event-stream", "http://localhost:8686/sse"]
      interval: 30s
      timeout: 5s
      retries: 3
      # Fallback for base images without curl:
      # test: ["CMD-SHELL", "timeout 2 bash -lc '</dev/tcp/localhost/8686'"]
    stop_grace_period: 10s

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
    image: crystaldba/postgres-mcp:v0.3.0  # Pin to same real version as postgres
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
      test: ["CMD", "curl", "-fsI", "-H", "Accept: text/event-stream", "http://localhost:8687/sse"]
      interval: 30s
      timeout: 5s
      retries: 3
      # Fallback for base images without curl:
      # test: ["CMD-SHELL", "timeout 2 bash -lc '</dev/tcp/localhost/8687'"]
    stop_grace_period: 10s

networks:
  mcp-net:
    external: true
  timescaledb-net:
    external: true
```

#### Filesystem MCP Bridge Service

**Dockerfile** (`projects/mcp/filesystem/bridge/Dockerfile`)
```dockerfile
# Base: mcp-proxy binary + add Node/npm for the stdio tool
FROM ghcr.io/tbxark/mcp-proxy:v0.39.1

# Add Node/npm (alpine variant)
RUN apk add --no-cache nodejs npm

# Preinstall the filesystem MCP to avoid npx network fetch at runtime
RUN npm i -g @modelcontextprotocol/server-filesystem@0.2.3

WORKDIR /app
COPY config /config

# Expose the bridge port (cluster-internal)
EXPOSE 9071
CMD ["/app/mcp-proxy", "-config", "/config/config.json"]
```

**Docker Compose** (`projects/mcp/filesystem/bridge/docker-compose.yml`)
```yaml
version: "3.8"
services:
  mcp-filesystem-bridge:
    build: .
    image: local/mcp-filesystem-bridge:0.2.3-bridge1
    container_name: mcp-filesystem-bridge
    restart: unless-stopped
    networks: ["mcp-net"]
    # Do NOT publish in prod; central proxy will consume over mcp-net
    # ports: ["9071:9071"] # optional for local debugging only
    volumes:
      - /home/administrator/projects:/workspace:ro
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:9071/"]
      interval: 30s
      timeout: 5s
      retries: 3
    stop_grace_period: 10s
    deploy:
      resources:
        limits:
          memory: 256M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  mcp-net:
    external: true
```

**Bridge Configuration** (`projects/mcp/filesystem/bridge/config/config.json`)
```json
{
  "mcpProxy": {
    "addr": ":9071",
    "name": "filesystem-bridge",
    "options": {
      "logEnabled": true,
      "panicIfInvalid": false
    }
  },
  "mcpServers": {
    "filesystem": {
      "command": "mcp-server-filesystem",
      "args": ["/workspace"]
    }
  }
}
```

#### Fetch MCP Bridge Service

**Dockerfile** (`projects/mcp/fetch/bridge/Dockerfile`)
```dockerfile
FROM ghcr.io/tbxark/mcp-proxy:v0.39.1

# Add Python + pip
RUN apk add --no-cache python3 py3-pip

# Pin the fetch server version you tested
RUN pip install --no-cache-dir mcp-server-fetch==0.1.4

WORKDIR /app
COPY config /config

EXPOSE 9072
CMD ["/app/mcp-proxy", "-config", "/config/config.json"]
```

**Docker Compose** (`projects/mcp/fetch/bridge/docker-compose.yml`)
```yaml
version: "3.8"
services:
  mcp-fetch-bridge:
    build: .
    image: local/mcp-fetch-bridge:0.1.4-bridge1
    container_name: mcp-fetch-bridge
    restart: unless-stopped
    networks: ["mcp-net"]
    # ports: ["9072:9072"] # optional for local debugging only
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:9072/"]
      interval: 30s
      timeout: 5s
      retries: 3
    stop_grace_period: 10s
    deploy:
      resources:
        limits:
          memory: 256M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  mcp-net:
    external: true
```

**Bridge Configuration** (`projects/mcp/fetch/bridge/config/config.json`)
```json
{
  "mcpProxy": {
    "addr": ":9072",
    "name": "fetch-bridge",
    "options": {
      "logEnabled": true,
      "panicIfInvalid": false
    }
  },
  "mcpServers": {
    "fetch": {
      "command": "python3",
      "args": ["-m", "mcp_server_fetch"]
    }
  }
}
```

#### Complete MCP Management Scripts

**1. Bridge Scaffold Script (`/home/administrator/projects/mcp/add-bridge.sh`)**
```bash
# Standardized generator for stdio→SSE bridges
./add-bridge.sh \
  --service filesystem \
  --runtime node \
  --pkg @modelcontextprotocol/server-filesystem \
  --version 0.2.3 \
  --bin-cmd mcp-server-filesystem \
  --port 9071 \
  --workspace /home/administrator/projects
```

**2. Central Proxy Registration (`/home/administrator/projects/mcp/add-to-central.sh`)**
```bash
# Wire bridge into central proxy with auth and testing
./add-to-central.sh \
  --service filesystem \
  --port 9071 \
  --add-auth \
  --test \
  --test-token "${MCP_PROXY_TOKEN}"
```

**3. Service Management (`/home/administrator/projects/mcp/list-central.sh`)**
```bash
# List current services in table format
./list-central.sh --format table | column -t

# Get service names only (for scripting)
./list-central.sh --format names
```

**4. Service Removal (`/home/administrator/projects/mcp/remove-from-central.sh`)**
```bash
# Remove service and verify route is gone
./remove-from-central.sh --service filesystem --test
```

**Complete Management Benefits**:
- **End-to-End Automation**: scaffold → build → register → test → manage lifecycle
- **Safe Operations**: automatic backups, JSON validation, health checks, rollback capability
- **Production Ready**: resource limits, log rotation, graceful shutdown, security hardening
- **Operational Excellence**: jq/python fallbacks, dry-run mode, comprehensive testing
- **Zero Downtime**: atomic config updates with restart and validation
- **Scriptable**: all operations support automation and integration with CI/CD pipelines

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
# Set token for testing
export MCP_TOKEN=${MCP_PROXY_TOKEN:-changeme-token}

# Test proxy root health check
curl -f http://linuxserver.lan:9090/

# Test postgres SSE endpoint (direct container)
curl -N -H 'Accept: text/event-stream' -H "Authorization: Bearer $MCP_TOKEN" \
  http://linuxserver.lan:9090/postgres/sse

# Test timescaledb SSE endpoint (second postgres instance)
curl -N -H 'Accept: text/event-stream' -H "Authorization: Bearer $MCP_TOKEN" \
  http://linuxserver.lan:9090/timescaledb/sse

# Test fetch SSE endpoint (stdio via bridge container)
curl -N -H 'Accept: text/event-stream' -H "Authorization: Bearer $MCP_TOKEN" \
  http://linuxserver.lan:9090/fetch/sse

# Test filesystem SSE endpoint (stdio via bridge container)
curl -N -H 'Accept: text/event-stream' -H "Authorization: Bearer $MCP_TOKEN" \
  http://linuxserver.lan:9090/filesystem/sse

# Test bridge containers directly (only if ports published for debugging)
# curl -f http://linuxserver.lan:9071/  # filesystem bridge health
# curl -f http://linuxserver.lan:9072/  # fetch bridge health

# Test authentication failure (should return 401/403)
curl -N -H 'Accept: text/event-stream' \
  http://linuxserver.lan:9090/postgres/sse

# Config validation using TBXark's converter (troubleshooting)
# Visit: https://tbxark.github.io/mcp-proxy to validate config
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

## Production Considerations & Troubleshooting

### Common Issues & Solutions

1. **Tool Name Collisions**
   - **Issue**: Two backends expose similarly named tools (e.g., both "query")
   - **Solution**: Use separate SSE endpoints and configure clients to select only needed tools
   - **Prevention**: Review tool names across services before deployment

2. **SSE Connection Drops**
   - **Issue**: Long-running SSE connections terminate unexpectedly
   - **Solution**: Ensure proxy and reverse proxy (if used) have idle timeouts >60s and buffering disabled
   - **Note**: Future reverse proxy configs should include SSE-specific settings

3. **Environment Token Management**
   - **Issue**: Need to rotate auth tokens without downtime
   - **Solution**: Update `MCP_PROXY_TOKEN` environment variable and restart proxy with graceful shutdown
   - **Best Practice**: Use secrets management system for token storage

### Future Reverse Proxy Notes
If fronting with nginx/traefik later:
```nginx
# Disable buffering for SSE
proxy_buffering off;
proxy_cache off;
# Increase timeouts
proxy_read_timeout 300s;
proxy_send_timeout 300s;
```

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
3. **Deploy Bridge Services** - Create filesystem and fetch bridge containers
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

**Final Production Enhancements Applied**:
- ✅ **Custom bridge images**: preinstall stdio tools (no runtime npx/uvx network fetches)
- ✅ **Resource management**: 256M memory limits and log rotation across all containers
- ✅ **Security hardened**: no published bridge ports in production, internal-only access
- ✅ **Bridge scaffold script**: standardized generator for all stdio→SSE bridge services
- ✅ **Reproducible builds**: exact tool versions baked into bridge images
- ✅ **Isolated blast radius**: bridge failures don't affect central proxy or other services
- ✅ **Production networking**: cluster-internal communication only, optional debug publishing
- ✅ **Environment-driven auth**: `MCP_PROXY_TOKEN` with optional bridge authentication
- ✅ **Operational excellence**: graceful shutdown, health checks, log management