# LiteLLM v1.77.3-stable MCP Gateway Deployment Plan - Requirements Compliant

## Executive Summary

This plan deploys LiteLLM at `projects/litellm` and community-supported MCP tools at `projects/mcp/{services}` per your directory requirements. Each MCP runs in its own Docker container in separate service directories, and all are registered directly to LiteLLM as the central gateway.

**Key Architectural Decisions:**
- **Directory Structure**: LiteLLM at `projects/litellm`, MCPs at `projects/mcp/postgres`, `projects/mcp/n8n`, etc.
- **Community Tools**: Uses well-supported MCP implementations (crystaldba/postgres-mcp, etc.)
- **Service Isolation**: Each MCP in its own directory with docker-compose
- **Central Registration**: All MCPs registered to LiteLLM via mcp_servers configuration
- **No Modifications**: Uses official containers as wrappers, no code changes

---

## Directory Structure

```
/home/administrator/projects/
├── litellm/                          # LiteLLM deployment
│   ├── docker-compose.yml
│   ├── config.yaml
│   ├── .env
│   └── README.md
│
└── mcp/                              # MCP services
    ├── postgres/                     # PostgreSQL MCP
    │   ├── docker-compose.yml
    │   ├── .env
    │   └── README.md
    ├── n8n/                          # N8N MCP
    │   ├── docker-compose.yml
    │   ├── .env
    │   └── README.md
    ├── playwright/                   # Browser automation MCP
    │   ├── docker-compose.yml
    │   ├── .env
    │   └── README.md
    ├── fetch/                        # HTTP fetch MCP
    │   ├── docker-compose.yml
    │   ├── .env
    │   └── README.md
    ├── timescaledb/                  # TimescaleDB MCP
    │   ├── docker-compose.yml
    │   ├── .env
    │   └── README.md
    └── minio/                        # Object storage MCP
        ├── docker-compose.yml
        ├── .env
        └── README.md
```

---

## Community-Supported MCP Tools Selection

### PostgreSQL MCP: crystaldba/postgres-mcp ✅
**Why chosen:**
- **Active maintenance**: Regular updates and community support
- **Security**: Configurable access modes (restricted/unrestricted)
- **Features**: Query analysis, performance monitoring, index recommendations
- **Transports**: Supports both stdio and SSE
- **Replaces**: Deprecated official modelcontextprotocol/server-postgres

### N8N MCP: Community wrapper ✅
**Why chosen:**
- **Integration**: Works with existing N8N installations
- **API Access**: Uses N8N's REST API for workflow management
- **Community**: Active development for automation workflows

### Playwright MCP: Official server ✅
**Why chosen:**
- **Official Support**: Maintained by Playwright team
- **Browser Automation**: Complete web testing and automation
- **Docker Ready**: Well-containerized

### Fetch MCP: Official server ✅
**Why chosen:**
- **Official**: Part of Model Context Protocol servers
- **HTTP Requests**: Essential for web API interactions
- **Lightweight**: Simple, reliable implementation

### TimescaleDB MCP: Community extension ✅
**Why chosen:**
- **Time-series**: Specialized for your TimescaleDB setup
- **PostgreSQL Compatible**: Builds on postgres-mcp patterns
- **Analytics**: Time-series specific operations

### Minio MCP: Community S3-compatible ✅
**Why chosen:**
- **S3 Compatible**: Works with your existing Minio setup
- **Object Storage**: File upload/download operations
- **Community**: Well-supported implementation

---

## Deployment Configuration

### 1. LiteLLM Main Service (`projects/litellm/`)

#### docker-compose.yml
```yaml
version: '3.8'

services:
  litellm-proxy:
    image: ghcr.io/berriai/litellm:v1.77.3-stable
    container_name: litellm-proxy
    restart: unless-stopped
    networks:
      - mcp-net
    ports:
      - "4000:4000"
    volumes:
      - ./config.yaml:/app/config.yaml:ro
    env_file:
      - ./.env
    environment:
      - LITELLM_HOST=0.0.0.0
      - LITELLM_PORT=4000
    command: ["--config", "/app/config.yaml", "--detailed_debug"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

networks:
  mcp-net:
    driver: bridge
```

#### config.yaml
```yaml
# LiteLLM v1.77.3-stable Configuration

model_list:
  - model_name: "gpt-4o-mock"
    litellm_params:
      model: "mock-response"
      api_key: "mock-key"

virtual_keys:
  - api_key: "${VIRTUAL_KEY_ADMIN}"
    models: ["gpt-4o-mock"]
    user: "lan-admin"
    max_budget: 100.0

  - api_key: "${VIRTUAL_KEY_CLAUDE}"
    models: ["gpt-4o-mock"]
    user: "claude-code-cli"
    max_budget: 50.0

  - api_key: "${VIRTUAL_KEY_WEBUI}"
    models: ["gpt-4o-mock"]
    user: "open-webui"
    max_budget: 50.0

general_settings:
  master_key: "${LITELLM_MASTER_KEY}"
  detailed_debug: true

litellm_settings:
  mcp_aliases:
    "db": "postgres_mcp"
    "automation": "n8n_mcp"
    "browser": "playwright_mcp"
    "fetch": "fetch_mcp"
    "timescale": "timescaledb_mcp"
    "storage": "minio_mcp"

# Register all MCP services using Docker service names (robust networking)
mcp_servers:
  postgres_mcp:
    url: "http://postgres-mcp:8000"
    transport: "sse"
    description: "PostgreSQL database access and management"
    api_keys: ["${VIRTUAL_KEY_ADMIN}", "${VIRTUAL_KEY_CLAUDE}"]

  n8n_mcp:
    url: "http://n8n-mcp:8000"
    transport: "sse"
    description: "N8N workflow automation"
    api_keys: ["${VIRTUAL_KEY_ADMIN}"]

  playwright_mcp:
    url: "http://playwright-mcp:8000"
    transport: "sse"
    description: "Browser automation and web testing"
    api_keys: ["${VIRTUAL_KEY_ADMIN}", "${VIRTUAL_KEY_CLAUDE}"]

  fetch_mcp:
    url: "http://fetch-mcp:8000"
    transport: "sse"
    description: "HTTP requests and web API access"
    api_keys: ["${VIRTUAL_KEY_ADMIN}", "${VIRTUAL_KEY_CLAUDE}", "${VIRTUAL_KEY_WEBUI}"]

  timescaledb_mcp:
    url: "http://timescaledb-mcp:8000"
    transport: "sse"
    description: "TimescaleDB time-series operations"
    api_keys: ["${VIRTUAL_KEY_ADMIN}", "${VIRTUAL_KEY_CLAUDE}"]

  minio_mcp:
    url: "http://minio-mcp:8000"
    transport: "sse"
    description: "Object storage operations"
    api_keys: ["${VIRTUAL_KEY_ADMIN}", "${VIRTUAL_KEY_WEBUI}"]
```

#### .env
```bash
# LiteLLM Configuration
LITELLM_MASTER_KEY=sk-litellm-master-$(openssl rand -hex 16)

# Virtual API Keys
VIRTUAL_KEY_ADMIN=lan-admin-key-$(openssl rand -hex 8)
VIRTUAL_KEY_CLAUDE=claude-code-key-$(openssl rand -hex 8)
VIRTUAL_KEY_WEBUI=open-webui-key-$(openssl rand -hex 8)
```

---

### 2. PostgreSQL MCP Service (`projects/mcp/postgres/`)

#### docker-compose.yml
```yaml
version: '3.8'

services:
  postgres-mcp:
    image: crystaldba/postgres-mcp:latest
    container_name: postgres-mcp
    restart: unless-stopped
    networks:
      - mcp-net
    ports:
      - "48001:8000"  # Optional: for debugging only
    environment:
      - DATABASE_URI=${DATABASE_URI}
    command: ["--access-mode=restricted", "--transport=sse"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  mcp-net:
    external: true  # Created by LiteLLM
```

#### .env
```bash
# PostgreSQL connection to your existing database
DATABASE_URI=postgresql://postgres:your_password@172.17.0.1:5432/postgres
```

---

### 3. N8N MCP Service (`projects/mcp/n8n/`)

#### docker-compose.yml
```yaml
version: '3.8'

services:
  n8n-mcp:
    image: ghcr.io/czlonkowski/n8n-mcp:latest
    container_name: n8n-mcp
    restart: unless-stopped
    networks:
      - mcp-net
    ports:
      - "48002:8000"  # Optional: for debugging only
    environment:
      - N8N_BASE_URL=${N8N_BASE_URL}
      - N8N_API_KEY=${N8N_API_KEY}
      - MCP_TRANSPORT=sse

networks:
  mcp-net:
    external: true  # Created by LiteLLM
```

#### .env
```bash
# N8N connection to your existing N8N instance
N8N_BASE_URL=http://172.17.0.1:5678
N8N_API_KEY=your_n8n_api_key
```

---

### 4. Playwright MCP Service (`projects/mcp/playwright/`)

#### docker-compose.yml
```yaml
version: '3.8'

services:
  playwright-mcp:
    image: ghcr.io/modelcontextprotocol/server-playwright:latest
    container_name: playwright-mcp
    restart: unless-stopped
    networks:
      - mcp-net
    ports:
      - "48003:8000"  # Optional: for debugging only
    environment:
      - MCP_TRANSPORT=sse
      - MCP_PORT=8000
    volumes:
      - /tmp:/tmp:rw

networks:
  mcp-net:
    external: true  # Created by LiteLLM
```

---

### 5. Fetch MCP Service (`projects/mcp/fetch/`)

#### docker-compose.yml
```yaml
version: '3.8'

services:
  fetch-mcp:
    image: ghcr.io/modelcontextprotocol/server-fetch:latest
    container_name: fetch-mcp
    restart: unless-stopped
    networks:
      - mcp-net
    ports:
      - "48004:8000"  # Optional: for debugging only
    environment:
      - MCP_TRANSPORT=sse

networks:
  mcp-net:
    external: true  # Created by LiteLLM
```

---

### 6. TimescaleDB MCP Service (`projects/mcp/timescaledb/`)

#### docker-compose.yml
```yaml
version: '3.8'

services:
  timescaledb-mcp:
    image: crystaldba/postgres-mcp:latest  # Same as postgres but different config
    container_name: timescaledb-mcp
    restart: unless-stopped
    networks:
      - mcp-net
    ports:
      - "48005:8000"  # Optional: for debugging only
    environment:
      - DATABASE_URI=${DATABASE_URI}
    command: ["--access-mode=restricted", "--transport=sse"]

networks:
  mcp-net:
    external: true  # Created by LiteLLM
```

#### .env
```bash
# TimescaleDB connection
DATABASE_URI=postgresql://postgres:your_password@172.17.0.1:5433/postgres
```

---

### 7. Minio MCP Service (`projects/mcp/minio/`)

#### docker-compose.yml
```yaml
version: '3.8'

services:
  minio-mcp:
    image: ghcr.io/modelcontextprotocol/server-s3:latest  # Community S3 MCP
    container_name: minio-mcp
    restart: unless-stopped
    networks:
      - mcp-net
    ports:
      - "48006:8000"  # Optional: for debugging only
    environment:
      - AWS_ENDPOINT_URL=${MINIO_ENDPOINT}
      - AWS_ACCESS_KEY_ID=${MINIO_ACCESS_KEY}
      - AWS_SECRET_ACCESS_KEY=${MINIO_SECRET_KEY}
      - MCP_TRANSPORT=sse

networks:
  mcp-net:
    external: true  # Created by LiteLLM
```

#### .env
```bash
# Minio S3-compatible connection
MINIO_ENDPOINT=http://172.17.0.1:9000
MINIO_ACCESS_KEY=your_minio_access_key
MINIO_SECRET_KEY=your_minio_secret_key
```

---

## Deployment Procedure

### Phase 1: Deploy LiteLLM Gateway (Creates shared network)

```bash
# Deploy LiteLLM first to create the shared mcp-net network
cd /home/administrator/projects/litellm
docker-compose up -d
```

### Phase 2: Deploy Individual MCP Services

```bash
# Deploy each MCP service - they will join the existing mcp-net network
cd /home/administrator/projects/mcp/postgres
docker-compose up -d

cd /home/administrator/projects/mcp/n8n
docker-compose up -d

cd /home/administrator/projects/mcp/playwright
docker-compose up -d

cd /home/administrator/projects/mcp/fetch
docker-compose up -d

cd /home/administrator/projects/mcp/timescaledb
docker-compose up -d

cd /home/administrator/projects/mcp/minio
docker-compose up -d
```

### Phase 3: Verification

```bash
# Test LiteLLM health
curl http://localhost:4000/health

# Test tool discovery
curl -H "Authorization: Bearer ${VIRTUAL_KEY_ADMIN}" \
     http://localhost:4000/v1/models | jq '.data[0].tools'

# Test specific MCP access
curl -H "Authorization: Bearer ${VIRTUAL_KEY_ADMIN}" \
     -H "x-mcp-servers: db,fetch" \
     http://localhost:4000/v1/models
```

---

## Client Integration

### Open-WebUI
```yaml
# Environment or admin settings
OPENAI_API_BASE_URL: "http://linuxserver.lan:4000/v1"
OPENAI_API_KEY: "${VIRTUAL_KEY_WEBUI}"
```

### Claude Code CLI
```bash
export CLAUDE_API_BASE="http://linuxserver.lan:4000/v1"
export CLAUDE_API_KEY="${VIRTUAL_KEY_CLAUDE}"
```

### VS Code
```json
{
  "claude.apiBase": "http://linuxserver.lan:4000/v1",
  "claude.apiKey": "${VIRTUAL_KEY_CLAUDE}"
}
```

---

## Maintenance & Operations

### Service Management
```bash
# Restart individual MCP service
cd /home/administrator/projects/mcp/postgres
docker-compose restart

# Update LiteLLM
cd /home/administrator/projects/litellm
docker-compose pull
docker-compose up -d
```

### Adding New MCPs
1. Create new directory: `/home/administrator/projects/mcp/{service}`
2. Add docker-compose.yml with MCP container
3. Update LiteLLM config.yaml with new mcp_servers entry
4. Restart LiteLLM: `docker-compose restart litellm-proxy`

### Monitoring
```bash
# Check all MCP services
for service in postgres n8n playwright fetch timescaledb minio; do
  echo "=== $service MCP ==="
  curl -f http://localhost:480$(printf "%02d" $(($(echo $service | wc -c) % 10 + 1)))/health
done

# Check LiteLLM logs
cd /home/administrator/projects/litellm
docker-compose logs -f litellm-proxy
```

---

## Executive Summary

This requirements-compliant plan provides:

**✅ Correct Directory Structure**: LiteLLM at `projects/litellm`, MCPs at `projects/mcp/{services}`
**✅ Community Tools**: Uses well-supported, actively maintained MCP implementations
**✅ Service Isolation**: Each MCP in its own directory with independent docker-compose
**✅ Central Registration**: All MCPs registered to LiteLLM as the single gateway
**✅ No Modifications**: Uses official containers as wrappers, no code changes
**✅ LAN Access**: All services accessible on linuxserver.lan
**✅ Client Ready**: Integration guides for Claude Code, Open-WebUI, VS Code
**✅ Maintainable**: Clear deployment, update, and monitoring procedures

**Deployment Timeline**: 2-3 hours for all services
**Scalability**: Easy to add new MCP services by following the pattern
**Success Criteria**: All MCP tools accessible via unified LiteLLM gateway on port 4000