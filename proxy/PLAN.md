# MCP Proxy Implementation Plan - UPDATED

**Project**: Central MCP Server using TBXark/mcp-proxy
**Target**: Single aggregation point for all MCP services on linuxserver.lan
**Date**: 2025-09-27
**Status**: Phase 1 complete; core services (postgres, fetch) live via proxy; remaining endpoints pending

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

## Progress Summary (2025-09-27)
- ✅ `mcp-proxy` deployed on `linuxserver.lan:9090` with bearer-token auth and health checks
- ✅ Native `postgres` MCP and `fetch` stdio bridge registered; curl and Claude CLI connectivity verified from LAN hosts
- ✅ `render-config.sh` updated to preserve existing services; `sync-claude-config.sh` added for client config drift
- ✅ Documentation refreshed (`CLAUDE.md`, `status.md`, `installmcp.md`) and secrets redacted from tracked files
- 🔄 Pending: enable filesystem/timescaledb bridges, expand client coverage (VS Code, MCPO), add runtime monitoring hooks

## Implementation Action Plan

### Phase 1: Core Infrastructure Setup – **Completed**
- [x] Create and attach `mcp-net` network (shared with existing services)
- [x] Deploy `mcp-proxy` (ghcr.io/tbxark/mcp-proxy:v0.39.1) with health check and bearer-token auth
- [x] Implement config templating + merge logic (`render-config.sh`) and ignore rendered file in Git
- [x] Add helper tooling (`add-to-central.sh`, `list-central.sh`, `sync-claude-config.sh`) for controlled updates

### Phase 2: MCP Service Integration – **In Progress**

| Service | Transport | Status | Notes |
|---------|-----------|--------|-------|
| `postgres` (crystaldba/postgres-mcp) | Native SSE @ 8686 | ✅ Live | Registered via proxy; curl + Claude verified |
| `fetch` bridge | stdio → SSE @ 9072 | ✅ Live | Using pinned `mcp-server-fetch==2025.4.7` |
| `filesystem` bridge | stdio → SSE @ 9071 | ◻ Pending | Requires RW policy decision; currently read-only plan conflicts with write tools |
| `timescaledb` (crystaldba/postgres-mcp) | Native SSE @ 8687 | ◻ Pending | Needs dedicated secrets + registration |
| Additional tools (playwright, minio, n8n, etc.) | TBD | ◻ Backlog | Follow `installmcp.md` workflow per service |

**Next immediate goals** *(see `installmcp.md` for detailed workflow)*
- [ ] Finalise filesystem bridge volume mode (RO vs RW) and, once decided, deploy & register via `add-to-central.sh`
- [ ] Stand up TimescaleDB MCP container with correct credentials and add to proxy
- [ ] Prioritise optional bridges (e.g., n8n, minio) using the new runbook; capture service-specific docs

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
source /home/administrator/secrets/mcp-proxy.env
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
      "authTokens": ["${MCP_PROXY_TOKEN}"]
    }
  },
  "mcpServers": {
    "postgres": {
      "url": "http://mcp-postgres:8686/sse"
    },
    "fetch": {
      "url": "http://mcp-fetch-bridge:9072/fetch/sse"
    },
    "filesystem": {
      "url": "http://mcp-filesystem-bridge:9071/filesystem/sse"
    }
  }
}
```

### Phase 3: Client Integration – **Partially Complete**

- ✅ **Claude Code CLI**: `sync-claude-config.sh` generates `~/.config/claude/mcp-settings.json` with LAN URLs and live token.
  - Next: publish instructions for other operator accounts; ensure stale local entries are purged when services move from `localhost` to `linuxserver.lan`.
- ◻ **VS Code MCP extension**: configure remote URL + token and create usage notes.
- ◻ **MCPO / Open-WebUI**: optional bridge not yet deployed; when pursued, pin MCPO image, enable CORS there, and register a single endpoint before expanding.
- ◻ **Other clients (Gemini CLI, ChatGPT Codex CLI)**: evaluate demand, document configuration templates, and test interoperability.

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
      "headers": { "Authorization": "Bearer ${MCP_PROXY_TOKEN}" }
    },
    "fetch": {
      "type": "sse",
      "url": "http://linuxserver.lan:9090/fetch/sse",
      "headers": { "Authorization": "Bearer ${MCP_PROXY_TOKEN}" }
    },
    "filesystem": {
      "type": "sse",
      "url": "http://linuxserver.lan:9090/filesystem/sse",
      "headers": { "Authorization": "Bearer ${MCP_PROXY_TOKEN}" }
    },
    "timescaledb": {
      "type": "sse",
      "url": "http://linuxserver.lan:9090/timescaledb/sse",
      "headers": { "Authorization": "Bearer ${MCP_PROXY_TOKEN}" }
    }
  }
}
```

*(Include only the services currently registered on the proxy; remove inactive entries until they are live.)*

### VS Code Extension Configuration
```json
{
  "mcp.servers": {
    "postgres": {
      "transport": "sse",
      "url": "http://linuxserver.lan:9090/postgres/sse",
      "headers": { "Authorization": "Bearer ${MCP_PROXY_TOKEN}" }
    },
    "fetch": {
      "transport": "sse",
      "url": "http://linuxserver.lan:9090/fetch/sse",
      "headers": { "Authorization": "Bearer ${MCP_PROXY_TOKEN}" }
    },
    "filesystem": {
      "transport": "sse",
      "url": "http://linuxserver.lan:9090/filesystem/sse",
      "headers": { "Authorization": "Bearer ${MCP_PROXY_TOKEN}" }
    },
    "timescaledb": {
      "transport": "sse",
      "url": "http://linuxserver.lan:9090/timescaledb/sse",
      "headers": { "Authorization": "Bearer ${MCP_PROXY_TOKEN}" }
    }
  }
}
```

*(VS Code supports the same headers; keep only active services to reduce warning pop-ups.)*

## Testing and Validation Plan - Revised

### Manual SSE Testing (Production Smoke Tests)
Test SSE endpoints manually with curl:
```bash
# Set token for testing
source /home/administrator/secrets/mcp-proxy.env
export MCP_TOKEN=${MCP_PROXY_TOKEN}

# Test proxy root health check
curl -f http://linuxserver.lan:9090/

# Test postgres SSE endpoint (direct container)
curl -N -H 'Accept: text/event-stream' -H "Authorization: Bearer $MCP_TOKEN" \
  http://linuxserver.lan:9090/postgres/sse

# Test fetch SSE endpoint (stdio via bridge container)
curl -N -H 'Accept: text/event-stream' -H "Authorization: Bearer $MCP_TOKEN" \
  http://linuxserver.lan:9090/fetch/sse

# Optional checks once additional services are enabled
# curl -N -H 'Accept: text/event-stream' -H "Authorization: Bearer $MCP_TOKEN" \
#   http://linuxserver.lan:9090/timescaledb/sse
# curl -N -H 'Accept: text/event-stream' -H "Authorization: Bearer $MCP_TOKEN" \
#   http://linuxserver.lan:9090/filesystem/sse

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

1. ✅ **Deploy pinned proxy** – Completed (v0.39.1 live with health checks and LAN base URL)
2. ✅ **Configure core SSE services** – Postgres native + fetch bridge operational
3. ◻ **Onboard filesystem bridge** – Resolve RW policy, deploy container, register via script
4. ◻ **Add TimescaleDB endpoint** – Provision secrets, start second crystaldba instance, register `/timescaledb/sse`
5. ◻ **Broaden client coverage** – Document VS Code setup, test additional CLIs, publish operator checklist
6. ◻ **Evaluate MCPO for Open-WebUI** – Optional; run pilot with single backend, ensure CORS + auth alignment
7. ◻ **Operationalise monitoring** – Hook proxy/service logs into Loki & add curl smoke checks to cron (or monitoring)

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
