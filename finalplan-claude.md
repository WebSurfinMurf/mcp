# LiteLLM v1.77.3-stable MCP Gateway Deployment Plan for linuxserver.lan

## Executive Summary

Based on deep analysis of your existing linuxserver.lan infrastructure and LiteLLM v1.77.3-stable capabilities, this plan leverages your already-built MCP containers and established Docker ecosystem to create a robust, LAN-accessible MCP gateway. The approach uses **SSE transport exclusively** for containerized MCPs, avoiding stdio complexities while maintaining your requirement for no MCP modifications.

**Key Architectural Decisions:**
- **SSE Transport**: All MCPs exposed via Server-Sent Events for clean Docker networking
- **Existing Infrastructure**: Leverage your PostgreSQL/TimescaleDB and built MCP containers
- **Docker Compose**: Declarative deployment with health checks and dependency management
- **Traefik Integration**: Use existing reverse proxy for domain access
- **Security First**: Network isolation, access controls, and secret management

---

## Current Infrastructure Analysis

### Existing Assets ✅
- **PostgreSQL**: Running on port 5432 (postgres:15)
- **TimescaleDB**: Running on port 5433 (timescale/timescaledb:latest-pg16)
- **Built MCP Containers**:
  - `pilot-mcp-postgresql:latest`
  - `mcp-timescaledb:latest`
  - `mcp-n8n:latest`
  - `mcp-playwright:latest`
  - `minio` (service running)
- **LiteLLM Images**: `litellm-custom:latest`, `ghcr.io/berriai/litellm-database:main-stable`
- **Network Infrastructure**: Traefik proxy with linuxserver.lan domain support

### Containers Already Running
- **Open-WebUI**: Port 8000 (ready for LiteLLM integration)
- **N8N**: Port 5678 (automation workflows)
- **Traefik**: Full reverse proxy setup
- **PostgreSQL/TimescaleDB**: Database backends available

---

## Refined Architecture: SSE-First MCP Gateway

### Why SSE Over Stdio?

**Problem with Stdio in Docker:**
- Complex volume mounting for dependencies
- Process lifecycle management issues
- Inter-container communication limitations
- Debugging and monitoring difficulties

**SSE Advantages:**
- Clean HTTP-based communication
- Docker service discovery via DNS
- Health checks and monitoring
- Horizontal scaling capability
- No filesystem coupling

### Network Architecture

```
Internet/LAN
    ↓
Traefik Proxy (linuxserver.lan)
    ↓
LiteLLM Proxy (:4000)
    ↓ (SSE/HTTP)
MCP Network (mcp-bridge)
├── MCP-PostgreSQL (:8001)
├── MCP-TimescaleDB (:8002)
├── MCP-N8N (:8003)
├── MCP-Playwright (:8004)
└── MCP-Minio (:8005)
```

---

## Deployment Configuration

### 1. docker-compose.yml

```yaml
version: '3.8'

networks:
  mcp-bridge:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
  traefik:
    external: true

volumes:
  litellm_data:
    driver: local

services:
  # Core LiteLLM Proxy Service
  litellm-proxy:
    image: ghcr.io/berriai/litellm-database:main-stable  # Use existing stable image
    container_name: mcp-litellm-gateway
    restart: unless-stopped
    networks:
      - mcp-bridge
      - traefik
    ports:
      - "4000:4000"
    volumes:
      - ./config/litellm-config.yaml:/app/config.yaml:ro
      - litellm_data:/app/data
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
      - DATABASE_URL=${LITELLM_DATABASE_URL}
      - LITELLM_HOST=0.0.0.0
      - LITELLM_PORT=4000
    command: ["--config", "/app/config.yaml", "--detailed_debug"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.litellm.rule=Host(`litellm.linuxserver.lan`)"
      - "traefik.http.routers.litellm.tls=true"
      - "traefik.http.services.litellm.loadbalancer.server.port=4000"

  # PostgreSQL MCP Server (SSE)
  mcp-postgresql:
    image: pilot-mcp-postgresql:latest  # Use your existing image
    container_name: mcp-postgresql-sse
    restart: unless-stopped
    networks:
      - mcp-bridge
    ports:
      - "8001:8000"  # Expose for debugging
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/postgres
      - MCP_TRANSPORT=sse
      - MCP_PORT=8000
      - MCP_HOST=0.0.0.0
    external_links:
      - postgres:postgres  # Link to existing PostgreSQL
    depends_on:
      - postgres-health-check

  # TimescaleDB MCP Server (SSE)
  mcp-timescaledb:
    image: mcp-timescaledb:latest
    container_name: mcp-timescaledb-sse
    restart: unless-stopped
    networks:
      - mcp-bridge
    ports:
      - "8002:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:${TIMESCALE_PASSWORD}@timescaledb:5432/postgres
      - MCP_TRANSPORT=sse
      - MCP_PORT=8000
      - MCP_HOST=0.0.0.0
    external_links:
      - timescaledb:timescaledb

  # N8N MCP Server (SSE)
  mcp-n8n:
    image: mcp-n8n:latest
    container_name: mcp-n8n-sse
    restart: unless-stopped
    networks:
      - mcp-bridge
    ports:
      - "8003:8000"
    environment:
      - N8N_BASE_URL=http://n8n:5678
      - N8N_API_KEY=${N8N_API_KEY}
      - MCP_TRANSPORT=sse
      - MCP_PORT=8000
    external_links:
      - n8n:n8n

  # Playwright MCP Server (SSE)
  mcp-playwright:
    image: mcp-playwright:latest
    container_name: mcp-playwright-sse
    restart: unless-stopped
    networks:
      - mcp-bridge
    ports:
      - "8004:8000"
    environment:
      - MCP_TRANSPORT=sse
      - MCP_PORT=8000
      - PLAYWRIGHT_HEADLESS=true
    volumes:
      - /tmp:/tmp:rw  # For downloads/screenshots

  # Minio MCP Server (SSE)
  mcp-minio:
    image: mcp-minio:latest  # Build if not exists
    container_name: mcp-minio-sse
    restart: unless-stopped
    networks:
      - mcp-bridge
    ports:
      - "8005:8000"
    environment:
      - MINIO_ENDPOINT=http://minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
      - MCP_TRANSPORT=sse
      - MCP_PORT=8000
    external_links:
      - minio:minio

  # Health check service for external dependencies
  postgres-health-check:
    image: postgres:15-alpine
    container_name: postgres-health-check
    networks:
      - mcp-bridge
    external_links:
      - postgres:postgres
    command: ["sh", "-c", "until pg_isready -h postgres -p 5432; do sleep 1; done"]
    restart: "no"
```

### 2. LiteLLM Configuration (config/litellm-config.yaml)

```yaml
# LiteLLM v1.77.3-stable Configuration
# Optimized for linuxserver.lan MCP deployment

model_list:
  # Mock model for testing
  - model_name: "gpt-4o-mock"
    litellm_params:
      model: "mock-response"
      api_key: "mock-key"

  # Add real models as needed
  # - model_name: "claude-3-sonnet"
  #   litellm_params:
  #     model: "anthropic/claude-3-sonnet-20240229"
  #     api_key: os.environ/ANTHROPIC_API_KEY

# Database configuration for logging/keys
litellm_settings:
  database_url: ${LITELLM_DATABASE_URL}

  # MCP Server Aliases - Clean tool namespacing
  mcp_aliases:
    "db": "mcp_postgresql"
    "timescale": "mcp_timescaledb"
    "automation": "mcp_n8n"
    "browser": "mcp_playwright"
    "storage": "mcp_minio"

# MCP Server Registration - SSE Transport
mcp_servers:
  mcp_postgresql:
    url: "http://mcp-postgresql:8000/sse"
    transport: "sse"
    description: "PostgreSQL database access and management"

  mcp_timescaledb:
    url: "http://mcp-timescaledb:8000/sse"
    transport: "sse"
    description: "TimescaleDB time-series data operations"

  mcp_n8n:
    url: "http://mcp-n8n:8000/sse"
    transport: "sse"
    description: "N8N workflow automation and management"

  mcp_playwright:
    url: "http://mcp-playwright:8000/sse"
    transport: "sse"
    description: "Web automation and browser testing"

  mcp_minio:
    url: "http://mcp-minio:8000/sse"
    transport: "sse"
    description: "Object storage operations"

# Virtual API Keys
virtual_keys:
  - api_key: "lan-admin-key-2024"
    models: ["gpt-4o-mock"]
    user: "lan-admin"
    max_budget: 100.0

  - api_key: "claude-code-key-2024"
    models: ["gpt-4o-mock"]
    user: "claude-code-cli"
    max_budget: 50.0

  - api_key: "open-webui-key-2024"
    models: ["gpt-4o-mock"]
    user: "open-webui"
    max_budget: 50.0

# General settings
general_settings:
  master_key: ${LITELLM_MASTER_KEY}
  database_type: "custom"  # Use your existing PostgreSQL
  custom_auth: "https://api.example.com/auth"  # Optional

# Logging and monitoring
litellm_logging:
  success_callback: ["prometheus"]
  failure_callback: ["prometheus"]
```

### 3. Environment Configuration (.env)

```bash
# LiteLLM Gateway Configuration
LITELLM_MASTER_KEY=sk-litellm-master-$(openssl rand -hex 16)
LITELLM_DATABASE_URL=postgresql://litellm:secure_password@postgres:5432/litellm

# Database Passwords (use existing or set new)
POSTGRES_PASSWORD=your_existing_postgres_password
TIMESCALE_PASSWORD=your_existing_timescale_password

# API Keys for services
N8N_API_KEY=your_n8n_api_key
MINIO_ACCESS_KEY=your_minio_access_key
MINIO_SECRET_KEY=your_minio_secret_key

# Optional LLM Provider Keys
# ANTHROPIC_API_KEY=your_anthropic_key
# OPENAI_API_KEY=your_openai_key
```

---

## Security & Best Practices

### Network Security
- **Isolated Network**: `mcp-bridge` network isolates MCP services
- **External Links**: Secure connections to existing services
- **Traefik Integration**: TLS termination and domain routing
- **Port Management**: Limited external exposure

### Access Control
- **Virtual Keys**: Per-service API key isolation
- **Budget Limits**: Cost controls per user/service
- **MCP Aliases**: Clean tool namespacing prevents conflicts
- **Environment Secrets**: Externalized sensitive configuration

### Monitoring & Debugging
- **Health Checks**: Service availability monitoring
- **Detailed Debug**: Enhanced logging for troubleshooting
- **Prometheus Metrics**: Integration with existing monitoring
- **Service Discovery**: Docker DNS for reliable connectivity

---

## Deployment Procedure

### Phase 1: Preparation
```bash
# Create deployment directory
mkdir -p /home/administrator/projects/mcp/litellm-gateway/{config,data,logs}
cd /home/administrator/projects/mcp/litellm-gateway

# Set secure permissions
chmod 700 .
```

### Phase 2: Configuration
```bash
# Create configuration files
cp [config files above] ./

# Generate secure passwords
openssl rand -hex 32 > .master_key
chmod 600 .master_key .env

# Validate configuration
docker-compose config
```

### Phase 3: Staged Deployment
```bash
# Start core services first
docker-compose up -d postgres-health-check
docker-compose up -d litellm-proxy

# Start MCP services incrementally
docker-compose up -d mcp-postgresql
docker-compose up -d mcp-timescaledb
docker-compose up -d mcp-n8n
docker-compose up -d mcp-playwright
docker-compose up -d mcp-minio
```

### Phase 4: Verification
```bash
# Health check
curl -H "Authorization: Bearer lan-admin-key-2024" \
     http://litellm.linuxserver.lan/v1/models

# Tool discovery test
curl -H "Authorization: Bearer lan-admin-key-2024" \
     -H "x-mcp-servers: db,timescale" \
     http://litellm.linuxserver.lan/v1/models

# Integration test
curl -X POST http://litellm.linuxserver.lan/v1/chat/completions \
     -H "Authorization: Bearer lan-admin-key-2024" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-4o-mock",
       "messages": [{"role": "user", "content": "List available tools"}],
       "tools": [{"type": "mcp_server", "server": "db"}]
     }'
```

---

## Client Integration Guide

### Open-WebUI Configuration
```yaml
# Open-WebUI environment update
OPENAI_API_BASE_URL: "http://litellm.linuxserver.lan"
OPENAI_API_KEY: "open-webui-key-2024"
```

### Claude Code CLI
```bash
# Add to ~/.claude/config.json
{
  "api_base": "http://litellm.linuxserver.lan",
  "api_key": "claude-code-key-2024"
}
```

### VS Code Integration
```json
// settings.json
{
  "mcp.servers": {
    "litellm": {
      "command": "curl",
      "args": [
        "-H", "Authorization: Bearer lan-admin-key-2024",
        "http://litellm.linuxserver.lan/v1/chat/completions"
      ]
    }
  }
}
```

---

## Maintenance & Monitoring

### Log Management
```bash
# Centralized logging
docker-compose logs -f litellm-proxy
docker-compose logs -f mcp-postgresql

# Performance monitoring
curl http://litellm.linuxserver.lan/metrics
```

### Updates & Scaling
```bash
# Update single MCP service
docker-compose pull mcp-postgresql
docker-compose up -d mcp-postgresql

# Scale specific services
docker-compose up -d --scale mcp-playwright=2
```

### Backup Strategy
```bash
# Configuration backup
tar -czf litellm-gateway-config-$(date +%Y%m%d).tar.gz config/ .env

# Database backup via existing PostgreSQL setup
pg_dump -h postgres -U litellm litellm > litellm-backup-$(date +%Y%m%d).sql
```

---

## Troubleshooting Guide

### Common Issues & Solutions

**1. MCP Server Connection Failed**
```bash
# Check network connectivity
docker exec mcp-litellm-gateway curl -v http://mcp-postgresql:8000/sse

# Verify MCP service health
docker-compose ps mcp-postgresql
docker-compose logs mcp-postgresql
```

**2. Tool Discovery Empty**
```bash
# Validate MCP server registration
curl -H "Authorization: Bearer lan-admin-key-2024" \
     http://litellm.linuxserver.lan/mcp/list_tools

# Check MCP server logs
docker-compose logs -f mcp-postgresql
```

**3. Authentication Issues**
```bash
# Verify virtual key configuration
docker exec mcp-litellm-gateway cat /app/config.yaml | grep -A5 virtual_keys

# Test key validity
curl -H "Authorization: Bearer lan-admin-key-2024" \
     http://litellm.linuxserver.lan/health
```

---

## Performance Optimization

### Resource Allocation
```yaml
# Add to docker-compose.yml services
deploy:
  resources:
    limits:
      memory: 512M
      cpus: "0.5"
    reservations:
      memory: 256M
      cpus: "0.25"
```

### Caching Strategy
```yaml
# Add Redis caching
litellm_settings:
  cache:
    type: "redis"
    host: "redis"
    port: 6379
    ttl: 3600
```

---

## Migration Path

### From Existing Setup
1. **Backup Current State**: Export existing configurations
2. **Parallel Deployment**: Run new stack alongside current
3. **Gradual Migration**: Move clients one by one
4. **Validation**: Comprehensive testing before cutover
5. **Cleanup**: Remove old containers after verification

### Future Enhancements
- **Load Balancing**: Multiple LiteLLM proxy instances
- **Auto-scaling**: Based on usage patterns
- **Advanced Monitoring**: Custom dashboards and alerting
- **Additional MCPs**: Expand tool ecosystem

---

## Executive Summary

This refined deployment plan leverages your existing linuxserver.lan infrastructure to create a production-ready LiteLLM MCP Gateway with the following key benefits:

**✅ Simplified Architecture**: SSE-only transport eliminates stdio complexities
**✅ Existing Infrastructure**: Reuses PostgreSQL, TimescaleDB, and built MCP containers
**✅ Network Security**: Isolated Docker networks with Traefik integration
**✅ Operational Ready**: Health checks, monitoring, and maintenance procedures
**✅ Client Ready**: Integration guides for Open-WebUI, Claude Code, and VS Code
**✅ Scalable**: Foundation for expanding MCP ecosystem

**Deployment Timeline**: 2-4 hours for complete setup and testing
**Maintenance**: Minimal ongoing overhead with automated health checks
**Success Criteria**: All MCPs accessible via unified LiteLLM gateway on linuxserver.lan

The plan prioritizes stability, security, and maintainability while providing the flexibility to expand your MCP ecosystem as needed.