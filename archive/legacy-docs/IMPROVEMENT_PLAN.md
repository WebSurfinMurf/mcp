# MCP Infrastructure Improvement Plan

## Executive Summary
Based on external analysis and current pain points, this plan proposes a complete restructure of the MCP deployment using docker-compose, individual containerization of each MCP server, and enhanced observability integration.

## Current State Problems
1. **Dependency Hell**: Single proxy container trying to run multiple runtimes (Node.js, Docker, NPX)
2. **Complex Process Management**: Proxy spawning stdio subprocesses with varied requirements
3. **Fragile Configuration**: Path dependencies, environment variables scattered
4. **Limited Scalability**: All MCPs in one proxy container
5. **Poor Observability**: No metrics, limited logging structure

## Proposed Architecture

### Phase 1: Containerize Each MCP Server
Instead of the proxy spawning stdio processes, each MCP will run in its own container with SSE/HTTP interface.

```
docker-compose stack
├── mcp-filesystem (Container 1)
├── mcp-memory (Container 2)  
├── mcp-fetch (Container 3)
├── mcp-monitoring (Container 4)
├── mcp-github (Container 5)
├── mcp-postgres (Container 6)
├── mcp-n8n (Container 7)
├── mcp-playwright (Container 8)
├── mcp-timescaledb (Container 9)
└── mcp-proxy (Container 10) - Optional, or use Traefik
```

### Phase 2: Individual Dockerfiles

#### 2.1 Filesystem MCP (Already Docker-based)
```dockerfile
# /home/administrator/projects/mcp/filesystem/Dockerfile
FROM mcp/filesystem:latest
# Already containerized, just needs SSE wrapper
```

#### 2.2 Memory MCP
```dockerfile
# /home/administrator/projects/mcp/memory-postgres/Dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 8080
CMD ["node", "src/server.js"]
```

#### 2.3 Monitoring MCP
```dockerfile
# /home/administrator/projects/mcp/monitoring/Dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY src/ ./src/
ENV LOKI_URL=http://loki:3100
ENV NETDATA_URL=http://netdata:19999
EXPOSE 8080
CMD ["node", "src/index.js"]
```

#### 2.4 Fetch MCP
```dockerfile
# /home/administrator/projects/mcp/fetch/Dockerfile
FROM mcp/fetch:latest
# Already containerized
```

#### 2.5 PostgreSQL MCP
```dockerfile
# /home/administrator/projects/mcp/postgres/Dockerfile
FROM crystaldba/postgres-mcp:latest
ENV PGHOST=postgres
ENV PGPORT=5432
ENV PGUSER=admin
ENV PGPASSWORD=${POSTGRES_PASSWORD}
ENV PGDATABASE=postgres
```

### Phase 3: Docker Compose Configuration

```yaml
# /home/administrator/projects/mcp/docker-compose.yml
version: '3.8'

networks:
  mcp-internal:
    driver: bridge
  traefik-net:
    external: true
  postgres-net:
    external: true
  loki-net:
    external: true

x-common-settings: &common
  restart: unless-stopped
  networks:
    - mcp-internal
    - traefik-net
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
      labels: "com.docker.compose.service,com.docker.compose.project"

services:
  # MCP Filesystem Service
  mcp-filesystem:
    <<: *common
    build:
      context: ./filesystem
      dockerfile: Dockerfile
    container_name: mcp-filesystem
    volumes:
      - /workspace:/workspace:ro
      - /home/administrator/projects:/projects:ro
    environment:
      - MCP_TRANSPORT=sse
      - MCP_PORT=8080
    ports:
      - "8501:8080"  # External port for testing
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp-filesystem.rule=Host(`mcp-filesystem.local`)"
      - "traefik.http.services.mcp-filesystem.loadbalancer.server.port=8080"
      - "com.mcp.type=filesystem"
      - "com.mcp.tools=11"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # MCP Memory Service
  mcp-memory:
    <<: *common
    build:
      context: ./memory-postgres
      dockerfile: Dockerfile
    container_name: mcp-memory
    networks:
      - mcp-internal
      - postgres-net
      - traefik-net
    environment:
      - PGHOST=postgres
      - PGPORT=5432
      - PGUSER=memory_user
      - PGPASSWORD=${MEMORY_DB_PASSWORD}
      - PGDATABASE=memory_db
      - MCP_TRANSPORT=sse
      - MCP_PORT=8080
    ports:
      - "8502:8080"
    labels:
      - "com.mcp.type=memory"
      - "com.mcp.backend=postgres"
    depends_on:
      - mcp-memory-init

  # Memory DB Initialization
  mcp-memory-init:
    image: postgres:15-alpine
    networks:
      - postgres-net
    environment:
      - PGHOST=postgres
      - PGPASSWORD=${POSTGRES_PASSWORD}
    command: |
      sh -c "
        until pg_isready -h postgres; do sleep 1; done
        psql -U admin -d postgres -c 'CREATE DATABASE IF NOT EXISTS memory_db;'
        psql -U admin -d postgres -c 'CREATE USER IF NOT EXISTS memory_user WITH PASSWORD '\''${MEMORY_DB_PASSWORD}'\'';'
        psql -U admin -d postgres -c 'GRANT ALL ON DATABASE memory_db TO memory_user;'
      "
    restart: "no"

  # MCP Monitoring Service
  mcp-monitoring:
    <<: *common
    build:
      context: ./monitoring
      dockerfile: Dockerfile
    container_name: mcp-monitoring
    networks:
      - mcp-internal
      - loki-net
      - traefik-net
    environment:
      - LOKI_URL=http://loki:3100
      - NETDATA_URL=http://netdata:19999
      - MCP_TRANSPORT=sse
      - MCP_PORT=8080
    ports:
      - "8503:8080"
    labels:
      - "com.mcp.type=monitoring"
      - "com.mcp.tools=5"
      - "com.mcp.datasources=loki,netdata"

  # MCP Fetch Service
  mcp-fetch:
    <<: *common
    image: mcp/fetch:latest
    container_name: mcp-fetch
    environment:
      - MCP_TRANSPORT=sse
      - MCP_PORT=8080
    ports:
      - "8504:8080"
    labels:
      - "com.mcp.type=fetch"
      - "com.mcp.capability=web-scraping"

  # MCP PostgreSQL Service
  mcp-postgres:
    <<: *common
    image: crystaldba/postgres-mcp:latest
    container_name: mcp-postgres-service
    networks:
      - mcp-internal
      - postgres-net
      - traefik-net
    environment:
      - PGHOST=postgres
      - PGPORT=5432
      - PGUSER=admin
      - PGPASSWORD=${POSTGRES_PASSWORD}
      - PGDATABASE=postgres
      - MCP_TRANSPORT=sse
      - MCP_PORT=8080
    ports:
      - "8505:8080"
    labels:
      - "com.mcp.type=postgres"
      - "com.mcp.capability=database"

  # Optional: Unified Gateway (replace sparfenyuk/mcp-proxy)
  mcp-gateway:
    <<: *common
    image: traefik:v3.0
    container_name: mcp-gateway
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.mcp.address=:8080"
    ports:
      - "8580:8080"  # MCP Gateway port
      - "8581:8081"  # Traefik dashboard
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    labels:
      - "traefik.enable=true"
      - "com.mcp.role=gateway"
```

### Phase 4: SSE Wrapper Implementation

For stdio-only MCPs, create a simple SSE wrapper:

```javascript
// /home/administrator/projects/mcp/common/sse-wrapper.js
const { spawn } = require('child_process');
const express = require('express');
const { v4: uuidv4 } = require('uuid');

class MCPSSEWrapper {
  constructor(command, args, env = {}) {
    this.command = command;
    this.args = args;
    this.env = { ...process.env, ...env };
    this.sessions = new Map();
    this.app = express();
    this.setupRoutes();
  }

  setupRoutes() {
    this.app.use(express.json());
    
    // SSE endpoint
    this.app.get('/sse', (req, res) => {
      res.setHeader('Content-Type', 'text/event-stream');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');
      
      const sessionId = uuidv4();
      const session = this.createSession(sessionId);
      this.sessions.set(sessionId, session);
      
      res.write(`event: endpoint\n`);
      res.write(`data: /messages/${sessionId}\n\n`);
      
      req.on('close', () => {
        this.closeSession(sessionId);
      });
    });
    
    // Message endpoint
    this.app.post('/messages/:sessionId', async (req, res) => {
      const { sessionId } = req.params;
      const session = this.sessions.get(sessionId);
      
      if (!session) {
        return res.status(404).json({ error: 'Session not found' });
      }
      
      try {
        const result = await this.sendToMCP(session, req.body);
        res.json(result);
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });
    
    // Health check
    this.app.get('/health', (req, res) => {
      res.json({ 
        status: 'healthy', 
        sessions: this.sessions.size,
        uptime: process.uptime()
      });
    });
  }

  createSession(sessionId) {
    const mcpProcess = spawn(this.command, this.args, {
      env: this.env,
      stdio: ['pipe', 'pipe', 'pipe']
    });
    
    return {
      id: sessionId,
      process: mcpProcess,
      buffer: '',
      callbacks: new Map()
    };
  }

  async sendToMCP(session, message) {
    return new Promise((resolve, reject) => {
      const messageId = message.id || uuidv4();
      
      session.callbacks.set(messageId, { resolve, reject });
      session.process.stdin.write(JSON.stringify(message) + '\n');
      
      // Set timeout
      setTimeout(() => {
        if (session.callbacks.has(messageId)) {
          session.callbacks.delete(messageId);
          reject(new Error('MCP request timeout'));
        }
      }, 30000);
    });
  }

  closeSession(sessionId) {
    const session = this.sessions.get(sessionId);
    if (session) {
      session.process.kill();
      this.sessions.delete(sessionId);
    }
  }

  start(port = 8080) {
    this.app.listen(port, '0.0.0.0', () => {
      console.log(`MCP SSE Wrapper listening on port ${port}`);
    });
  }
}

module.exports = MCPSSEWrapper;
```

### Phase 5: Deployment Scripts

```bash
#!/bin/bash
# /home/administrator/projects/mcp/deploy.sh

set -e

echo "=== MCP Stack Deployment ==="

# Install docker-compose if needed
if ! command -v docker-compose &> /dev/null; then
    echo "Installing docker-compose..."
    sudo apt-get update
    sudo apt-get install -y docker-compose
fi

# Load environment variables
source $HOME/projects/secrets/mcp.env

# Build all images
echo "Building MCP images..."
docker-compose build --parallel

# Deploy stack
echo "Deploying MCP stack..."
docker-compose up -d

# Wait for health checks
echo "Waiting for services to be healthy..."
sleep 10

# Verify deployment
docker-compose ps

# Show endpoints
echo ""
echo "=== MCP Endpoints ==="
echo "Filesystem: http://localhost:8501/sse"
echo "Memory:     http://localhost:8502/sse"
echo "Monitoring: http://localhost:8503/sse"
echo "Fetch:      http://localhost:8504/sse"
echo "PostgreSQL: http://localhost:8505/sse"
echo ""
echo "Gateway:    http://localhost:8580"
echo "Dashboard:  http://localhost:8581"
```

### Phase 6: Observability Integration

#### 6.1 Promtail Configuration Addition
```yaml
# Add to /home/administrator/projects/promtail/config.yml
- job_name: mcp-services
  docker_sd_configs:
    - host: unix:///var/run/docker.sock
      refresh_interval: 5s
      filters:
        - name: label
          values: ["com.mcp.*"]
  relabel_configs:
    - source_labels: ['__meta_docker_container_name']
      target_label: 'container_name'
    - source_labels: ['__meta_docker_container_label_com_mcp_type']
      target_label: 'mcp_type'
    - source_labels: ['__meta_docker_container_label_com_mcp_tools']
      target_label: 'mcp_tools_count'
```

#### 6.2 Grafana Dashboard
```json
{
  "dashboard": {
    "title": "MCP Services Monitor",
    "panels": [
      {
        "title": "MCP Service Status",
        "targets": [
          {
            "expr": "up{job='mcp-services'}",
            "legendFormat": "{{container_name}}"
          }
        ]
      },
      {
        "title": "MCP Request Rate",
        "targets": [
          {
            "expr": "rate(mcp_requests_total[5m])",
            "legendFormat": "{{mcp_type}}"
          }
        ]
      },
      {
        "title": "MCP Session Count",
        "targets": [
          {
            "expr": "mcp_active_sessions",
            "legendFormat": "{{container_name}}"
          }
        ]
      }
    ]
  }
}
```

### Phase 7: LiteLLM Integration

Update LiteLLM config to use new endpoints:

```yaml
# /home/administrator/projects/litellm/config.yaml
litellm_settings:
  mcp_servers:
    filesystem:
      transport: "sse"
      url: "http://mcp-filesystem:8080/sse"
      
    memory:
      transport: "sse"
      url: "http://mcp-memory:8080/sse"
      
    monitoring:
      transport: "sse"
      url: "http://mcp-monitoring:8080/sse"
      
    fetch:
      transport: "sse"
      url: "http://mcp-fetch:8080/sse"
      
    postgres:
      transport: "sse"
      url: "http://mcp-postgres-service:8080/sse"
```

## Implementation Timeline

### Week 1: Foundation
- [ ] Day 1-2: Install docker-compose, create base directory structure
- [ ] Day 3-4: Build Dockerfiles for filesystem, memory, monitoring
- [ ] Day 5-7: Create docker-compose.yml, test basic stack

### Week 2: Expansion
- [ ] Day 8-9: Add remaining MCP services (fetch, postgres, github)
- [ ] Day 10-11: Implement SSE wrapper for stdio-only services
- [ ] Day 12-14: Integration testing with LiteLLM

### Week 3: Production Readiness
- [ ] Day 15-16: Add health checks and monitoring
- [ ] Day 17-18: Integrate with Promtail/Loki/Grafana
- [ ] Day 19-21: Documentation and deployment automation

## Benefits of This Approach

1. **Isolation**: Each MCP runs in its own container with exact dependencies
2. **Scalability**: Can scale individual MCPs based on load
3. **Maintainability**: Clear separation of concerns, easy updates
4. **Observability**: Native integration with existing monitoring stack
5. **Reliability**: Health checks, automatic restarts, proper networking
6. **Security**: No Docker socket mounting in application containers
7. **Simplicity**: Docker-compose manages entire stack declaratively

## Risk Mitigation

1. **Gradual Migration**: Keep existing setup running while building new
2. **Testing Environment**: Use docker-compose profiles for staging
3. **Rollback Plan**: Keep backup of working configuration
4. **Monitoring**: Add alerts for service failures

## Success Metrics

- All 9 MCP services running independently
- Zero dependency conflicts
- < 100ms latency for MCP tool calls
- 99.9% uptime for critical MCPs (filesystem, monitoring)
- Successful integration with LiteLLM
- Full observability through Grafana

## Conclusion

This plan addresses all identified issues:
- Eliminates dependency hell through containerization
- Removes complex process management from proxy
- Provides clear, maintainable configuration
- Scales horizontally
- Integrates with existing infrastructure

The docker-compose approach is industry standard and will make the system more maintainable and reliable.

---
*Plan created: 2025-09-07*
*Estimated implementation: 3 weeks*
*Complexity: Medium*
*Risk: Low with gradual migration*