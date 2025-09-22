# MCP Proxy Implementation Plan

**Project**: Central MCP Server using TBXark/mcp-proxy
**Target**: Single aggregation point for all MCP services on linuxserver.lan
**Date**: 2025-09-21

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

## Architecture Overview

```
External Clients                Central Proxy              Individual MCP Services
┌─────────────────┐             ┌─────────────────┐        ┌─────────────────────────────┐
│ Claude Code CLI │────────┐    │                 │        │ projects/mcp/postgres       │
│ (stdio/HTTP)    │        │    │ TBXark/mcp-proxy│────────│ ├── mcp-postgres            │
├─────────────────┤        │    │                 │        │ └── docker-compose.yml      │
│ Gemini CLI      │────────┼────│ HTTP Server     │        ├─────────────────────────────┤
│ (HTTP)          │        │    │ Port: 9090      │────────│ projects/mcp/filesystem     │
├─────────────────┤        │    │                 │        │ ├── mcp-filesystem          │
│ ChatGPT Codex   │────────┤    │ Config-driven   │        │ └── docker-compose.yml      │
│ (HTTP)          │        │    │ Service routing │        ├─────────────────────────────┤
├─────────────────┤        │    │                 │────────│ projects/mcp/fetch          │
│ Open-WebUI      │────────┤    │ Aggregates:     │        │ ├── mcp-fetch               │
│ (HTTP)          │        │    │ - Tools         │        │ └── docker-compose.yml      │
├─────────────────┤        │    │ - Resources     │        ├─────────────────────────────┤
│ VS Code         │────────┘    │ - Prompts       │────────│ projects/mcp/timescaledb    │
│ (HTTP/stdio)    │             │                 │        │ ├── mcp-timescaledb         │
└─────────────────┘             └─────────────────┘        │ └── docker-compose.yml      │
                                                           └─────────────────────────────┘
```

## Implementation Action Plan

### Phase 1: Core Infrastructure Setup (Day 1)

#### 1.1 Network Configuration
```bash
# Create dedicated Docker network for MCP services
docker network create mcp-net --subnet=172.30.0.0/16
```

#### 1.2 Base Directory Structure
```
projects/mcp-proxy/
├── PLAN.md                     # This file
├── config/
│   ├── mcp-proxy.json         # Central proxy configuration
│   └── servers.json           # Individual server definitions
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

#### 1.3 Core Proxy Deployment
- Deploy TBXark/mcp-proxy container
- Configure basic HTTP server on port 9090
- Test basic connectivity from linuxserver.lan

### Phase 2: MCP Service Integration (Days 2-3)

#### 2.1 Priority MCP Services (Community-Supported)
Based on community adoption and your infrastructure needs:

1. **mcp-postgres** - Database operations (existing infrastructure)
2. **mcp-filesystem** - File operations
3. **mcp-fetch** - Web content retrieval
4. **mcp-timescaledb** - Time-series data (existing infrastructure)
5. **mcp-monitoring** - System observability (existing logs/metrics)

#### 2.2 Service Deployment Pattern
For each MCP service:
```bash
projects/mcp/{service}/
├── docker-compose.yml         # Service container definition
├── config/                    # Service-specific configuration
├── .env                       # Service environment variables
└── README.md                  # Service documentation
```

#### 2.3 Configuration Integration
Each service registered in central `mcp-proxy.json`:
```json
{
  "servers": [
    {
      "name": "postgres",
      "type": "stdio",
      "command": "docker",
      "args": ["exec", "mcp-postgres", "python", "-m", "mcp_postgres"]
    },
    {
      "name": "filesystem",
      "type": "sse",
      "url": "http://mcp-filesystem:8001/sse"
    }
  ]
}
```

### Phase 3: Client Integration (Days 4-5)

#### 3.1 Claude Code CLI Setup
- Configure `.claude/mcp_servers.json` to point to proxy
- Test tool discovery and execution
- Verify stdio and HTTP connectivity

#### 3.2 Open-WebUI Integration
- Configure MCP endpoint in Open-WebUI settings
- Test web-based tool access
- Verify authentication if required

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
- Service authentication (if required)
- Log aggregation and monitoring

#### 4.2 Health Monitoring
- Service health checks
- Proxy status monitoring
- Integration with existing observability stack (Loki/Grafana)

#### 4.3 Backup and Recovery
- Configuration backup procedures
- Service restart automation
- Disaster recovery documentation

## Detailed Configuration Specifications

### TBXark/mcp-proxy Configuration

#### Base Configuration (`config/mcp-proxy.json`)
```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 9090
  },
  "servers": [],
  "logging": {
    "level": "info",
    "file": "/logs/mcp-proxy.log"
  },
  "cors": {
    "enabled": true,
    "origins": ["*"]
  }
}
```

#### Docker Deployment (`docker-compose.yml`)
```yaml
version: '3.8'
services:
  mcp-proxy:
    image: ghcr.io/tbxark/mcp-proxy:latest
    container_name: mcp-proxy
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./config:/config
      - ./logs:/logs
      - /var/run/docker.sock:/var/run/docker.sock  # For stdio Docker exec
    networks:
      - mcp-net
      - default
    environment:
      - CONFIG_FILE=/config/mcp-proxy.json
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9090/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  mcp-net:
    external: true
```

### Individual MCP Service Templates

#### PostgreSQL MCP Service (`projects/mcp/postgres/docker-compose.yml`)
```yaml
version: '3.8'
services:
  mcp-postgres:
    image: mcp/postgres:latest  # Community image or custom build
    container_name: mcp-postgres
    restart: unless-stopped
    networks:
      - mcp-net
      - postgres-net  # Connect to existing DB network
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_USER=${POSTGRES_USER}
      - DB_PASSWORD=${POSTGRES_PASSWORD}
    env_file:
      - .env
    volumes:
      - ./config:/config
    healthcheck:
      test: ["CMD", "python", "-c", "import mcp_postgres; print('OK')"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  mcp-net:
    external: true
  postgres-net:
    external: true
```

#### Filesystem MCP Service (`projects/mcp/filesystem/docker-compose.yml`)
```yaml
version: '3.8'
services:
  mcp-filesystem:
    image: mcp/filesystem:latest
    container_name: mcp-filesystem
    restart: unless-stopped
    ports:
      - "8001:8001"  # SSE endpoint
    networks:
      - mcp-net
    volumes:
      - /home/administrator/projects:/workspace:ro  # Read-only project access
      - ./config:/config
    environment:
      - WORKSPACE_PATH=/workspace
      - SSE_PORT=8001
    env_file:
      - .env
```

## Client Connection Examples

### Claude Code CLI Configuration
```json
{
  "mcpServers": {
    "central-mcp": {
      "command": "curl",
      "args": ["-X", "POST", "http://linuxserver.lan:9090/mcp"],
      "env": {}
    }
  }
}
```

### Open-WebUI Configuration
```yaml
# In Open-WebUI environment
MCP_SERVERS: |
  {
    "central-mcp": {
      "url": "http://linuxserver.lan:9090",
      "name": "Central MCP Proxy"
    }
  }
```

### VS Code Extension Configuration
```json
{
  "mcp.servers": {
    "central-mcp": {
      "transport": "http",
      "url": "http://linuxserver.lan:9090"
    }
  }
}
```

## Testing and Validation Plan

### Functional Tests
1. **Proxy Health**: Verify proxy starts and responds on port 9090
2. **Service Discovery**: Confirm all MCP services are discoverable through proxy
3. **Tool Execution**: Test tools from each backend service work correctly
4. **Multi-Client**: Verify concurrent access from different clients
5. **Transport Types**: Test stdio, HTTP, and SSE transport modes

### Integration Tests
1. **Database Operations**: Execute SQL queries through mcp-postgres
2. **File Operations**: Read/write files through mcp-filesystem
3. **Web Fetching**: Retrieve web content through mcp-fetch
4. **Cross-Service**: Test workflows using multiple MCP services

### Performance Tests
1. **Concurrent Requests**: Multiple clients accessing simultaneously
2. **Large Responses**: Handle large data returns from services
3. **Network Latency**: Test performance across LAN
4. **Resource Usage**: Monitor proxy and service resource consumption

## Rollback and Recovery Plans

### Configuration Rollback
- Keep previous working configurations in `config/backup/`
- Automated config validation before deployment
- Quick rollback script for emergency situations

### Service Recovery
- Individual service restart procedures
- Proxy restart without affecting running services
- Network connectivity restoration procedures

### Disaster Recovery
- Complete infrastructure rebuild procedures
- Configuration and data backup locations
- Emergency contact and escalation procedures

## Success Metrics

### Technical Metrics
- **Uptime**: >99.5% proxy availability
- **Response Time**: <500ms for tool discovery
- **Concurrent Users**: Support 10+ simultaneous connections
- **Service Coverage**: All planned MCP services operational

### User Experience Metrics
- **Setup Time**: New client connection in <10 minutes
- **Tool Discovery**: All tools visible from all clients
- **Error Rate**: <1% failed tool executions
- **Documentation**: Complete setup guides for all supported clients

## Risk Assessment and Mitigation

### Technical Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Proxy failure | High | Low | Health monitoring, auto-restart, backup proxy |
| Service incompatibility | Medium | Medium | Thorough testing, version pinning |
| Network issues | Medium | Low | Network monitoring, redundant paths |
| Client compatibility | Medium | Medium | Multi-client testing, documentation |

### Operational Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Configuration drift | Medium | Medium | Version control, validation scripts |
| Service proliferation | Low | High | Standardized deployment procedures |
| Documentation lag | Medium | High | Automated documentation updates |
| Knowledge transfer | High | Low | Comprehensive documentation |

## Next Steps

1. **Review and Approve Plan** - Stakeholder review of implementation approach
2. **Environment Preparation** - Set up base directories and Docker networks
3. **Proof of Concept** - Deploy minimal proxy with one MCP service
4. **Iterative Expansion** - Add services incrementally with testing
5. **Client Integration** - Connect each client type systematically
6. **Production Deployment** - Full rollout with monitoring and documentation

---

**Implementation Owner**: Claude Code
**Review Required**: User approval before Phase 1 execution
**Estimated Timeline**: 6 days full implementation
**Dependencies**: Docker, existing postgres/observability infrastructure
**Success Criteria**: Single MCP endpoint accessible from all target clients on linuxserver.lan