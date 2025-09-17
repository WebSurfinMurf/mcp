# 3-Tool MCP Pilot Implementation Plan

**Project Goal**: Implement and test 3 proven MCP servers before proceeding with full 8-container architecture

**Date**: 2025-09-16
**Status**: Planning Phase - Ready for Implementation
**Scope**: Focus on filesystem, monitoring, and PostgreSQL tools using proven implementations

---

## Selected Proven MCP Implementations

Based on research and recommendations, these are the best-of-breed MCP servers for our pilot:

### 1. **PostgreSQL**: HenkDz/postgresql-mcp-server ✅ **RECOMMENDED**
- **Repository**: https://github.com/HenkDz/postgresql-mcp-server
- **Capabilities**: 17 intelligent database management tools through consolidation and enhancement
- **Protocol**: HTTP/stdio (more comprehensive than telegraph-it version)
- **Why This One**: More tools (17 vs basic implementations), actively maintained, proven quality

### 1. **PostgreSQL**: crystaldba/postgres-mcp ✅ **ALTERNATIVE CONSIDERED**
- **Repository**: https://github.com/crystaldba/postgres-mcp
- **Capabilities**: Performance analysis and monitoring for PostgreSQL
- **Note**: This is PostgreSQL-specific monitoring, need generic system monitoring

### 2. **Monitoring**: Custom System Monitoring ✅ **RECOMMENDED**
- **Approach**: Implement lightweight MCP server wrapping existing Loki/Netdata APIs
- **Capabilities**: System metrics, log search (leveraging existing infrastructure)
- **Why Custom**: No proven generic monitoring MCP found, but we have solid Loki/Netdata setup

### 3. **Filesystem**: Official modelcontextprotocol/servers filesystem ✅ **RECOMMENDED**
- **Repository**: https://github.com/modelcontextprotocol/servers (filesystem implementation)
- **Capabilities**: Secure file operations with path restrictions
- **Protocol**: stdio
- **Why This One**: Official implementation, security-focused, proven stable

---

## Implementation Plan

### Phase 1: Environment Preparation (Day 1)
**Deliverables**:
- [ ] Clean slate: Stop current mcp-server container
- [ ] Create new directory structure for pilot implementation
- [ ] Set up LiteLLM MCP configuration for 3 servers
- [ ] Document baseline state

**Technical Tasks**:
```bash
# Stop current MCP server
cd /home/administrator/projects/mcp/server
docker compose -f docker-compose.microservices.yml down

# Create pilot directory
mkdir -p /home/administrator/projects/mcp/pilot/{postgresql,monitoring,filesystem}
```

### Phase 2: PostgreSQL MCP Server (Day 2)
**Implementation**: HenkDz/postgresql-mcp-server
- [ ] Clone repository and review 17 available tools
- [ ] Configure for our PostgreSQL instance (postgres:5432)
- [ ] Create Docker container with proper networking
- [ ] Test basic connectivity and tool discovery
- [ ] Document all 17 tools and their capabilities

**Container Configuration**:
```yaml
services:
  mcp-postgresql:
    image: mcp-postgresql:latest
    container_name: mcp-postgresql
    networks: [mcp-pilot, postgres-net]
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=Pass123qp
    ports:
      - "8080:8080"  # SSE endpoint for LiteLLM
```

### Phase 3: Filesystem MCP Server (Day 3)
**Implementation**: Official modelcontextprotocol/servers filesystem
- [ ] Extract filesystem implementation from official repository
- [ ] Configure security restrictions for safe file access
- [ ] Create container with volume mounts for controlled access
- [ ] Test file read/write/list operations
- [ ] Validate security boundaries

**Container Configuration**:
```yaml
services:
  mcp-filesystem:
    image: mcp-filesystem:latest
    container_name: mcp-filesystem
    networks: [mcp-pilot]
    volumes:
      - /home/administrator/projects:/workspace:ro
      - /tmp:/tmp:rw
    environment:
      - ALLOWED_PATHS=/workspace,/tmp
    ports:
      - "8081:8080"  # SSE endpoint
```

### Phase 4: Monitoring MCP Server (Day 4)
**Implementation**: Custom lightweight wrapper
- [ ] Create minimal MCP server wrapping Loki/Netdata APIs
- [ ] Implement 3-4 essential monitoring tools
- [ ] Test log search and system metrics retrieval
- [ ] Ensure proper error handling and timeouts

**Tools to Implement**:
1. `search_logs` - LogQL queries to Loki
2. `get_system_metrics` - Netdata CPU/memory/disk
3. `get_container_status` - Docker container health
4. `get_recent_errors` - Last 24h error summary

**Container Configuration**:
```yaml
services:
  mcp-monitoring:
    image: mcp-monitoring:latest
    container_name: mcp-monitoring
    networks: [mcp-pilot, observability-net]
    environment:
      - LOKI_URL=http://loki:3100
      - NETDATA_URL=http://netdata:19999
    ports:
      - "8082:8080"  # SSE endpoint
```

### Phase 5: LiteLLM Integration Testing (Day 5)
**Deliverables**:
- [ ] Configure LiteLLM with 3 MCP servers
- [ ] Test SSE connections and tool discovery
- [ ] Validate each tool works through LiteLLM
- [ ] Test with OpenWebUI end-to-end
- [ ] Document any issues or limitations

**LiteLLM Configuration**:
```yaml
# Add to /home/administrator/projects/litellm/config.yaml
litellm_settings:
  mcp_servers:
    postgresql:
      transport: "http"
      url: "http://mcp-postgresql:8080"
      description: "PostgreSQL database operations (17 tools)"
    filesystem:
      transport: "http"
      url: "http://mcp-filesystem:8081"
      description: "Secure file operations"
    monitoring:
      transport: "http"
      url: "http://mcp-monitoring:8082"
      description: "System monitoring and logs"
```

---

## Success Criteria

### Technical Validation
- [ ] All 3 MCP servers start successfully and report healthy
- [ ] LiteLLM discovers all tools from 3 servers
- [ ] Each tool can be executed individually through HTTP API
- [ ] No container restart loops or connectivity issues
- [ ] Response times under 2 seconds for typical operations

### Integration Validation
- [ ] OpenWebUI can access models through LiteLLM
- [ ] Models can automatically call MCP tools when contextually appropriate
- [ ] Tool calls execute successfully and return proper results
- [ ] Error handling works gracefully for failed tool calls
- [ ] No impact on existing OpenWebUI functionality

### Functional Validation
**PostgreSQL Tools** (minimum 5 working):
- [ ] List databases and tables
- [ ] Execute read-only queries
- [ ] Get database statistics
- [ ] Validate connection pooling
- [ ] Test concurrent access

**Filesystem Tools** (minimum 3 working):
- [ ] List directory contents (with security restrictions)
- [ ] Read file contents safely
- [ ] Write files to allowed locations
- [ ] Validate path security enforcement

**Monitoring Tools** (minimum 3 working):
- [ ] Search recent logs with LogQL
- [ ] Get current system metrics
- [ ] Check container health status
- [ ] Validate data freshness

---

## Docker Compose Configuration

### Network Setup
```yaml
networks:
  mcp-pilot:
    driver: bridge
    ipam:
      config:
        - subnet: 172.30.0.0/24
  postgres-net:
    external: true
  observability-net:
    external: true
```

### Complete Stack
```yaml
version: '3.8'
services:
  mcp-postgresql:
    build: ./postgresql
    container_name: mcp-postgresql
    networks: [mcp-pilot, postgres-net]
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=Pass123qp
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      retries: 3

  mcp-filesystem:
    build: ./filesystem
    container_name: mcp-filesystem
    networks: [mcp-pilot]
    volumes:
      - /home/administrator/projects:/workspace:ro
      - /tmp:/tmp:rw
    environment:
      - ALLOWED_PATHS=/workspace,/tmp
    ports:
      - "8081:8080"

  mcp-monitoring:
    build: ./monitoring
    container_name: mcp-monitoring
    networks: [mcp-pilot, observability-net]
    environment:
      - LOKI_URL=http://loki:3100
      - NETDATA_URL=http://netdata:19999
    ports:
      - "8082:8080"
```

---

## Risk Assessment

### Technical Risks
- **Risk**: MCP server implementations may not work with our infrastructure
  - **Mitigation**: Start with PostgreSQL (most critical), verify before proceeding
- **Risk**: LiteLLM MCP integration may have bugs
  - **Mitigation**: Test with minimal setup first, document workarounds
- **Risk**: Performance impact on existing services
  - **Mitigation**: Use separate network, monitor resource usage

### Implementation Risks
- **Risk**: Official filesystem MCP may be too restrictive
  - **Mitigation**: Test with specific file paths, adjust security as needed
- **Risk**: Custom monitoring implementation introduces bugs
  - **Mitigation**: Keep implementation minimal, reuse existing API calls
- **Risk**: Container networking complexity
  - **Mitigation**: Use proven patterns from existing infrastructure

### Mitigation Strategies
- **Incremental Testing**: Validate each MCP server independently before integration
- **Rollback Plan**: Keep current mcp-server configuration as backup
- **Monitoring**: Track resource usage and performance impact
- **Documentation**: Record all issues and solutions for full implementation

---

## Timeline and Resources

### Development Schedule
- **Day 1**: Environment setup and baseline (4 hours)
- **Day 2**: PostgreSQL MCP implementation and testing (6 hours)
- **Day 3**: Filesystem MCP implementation and testing (6 hours)
- **Day 4**: Monitoring MCP implementation and testing (6 hours)
- **Day 5**: LiteLLM integration and end-to-end testing (8 hours)
- **Total**: 30 hours over 5 days

### Success Metrics
- **Week 1**: 3 MCP servers operational with basic tool functionality
- **Integration Test**: LiteLLM successfully discovers and executes all tools
- **End-to-End Test**: OpenWebUI users can ask questions that trigger tool usage
- **Go/No-Go Decision**: Proceed with full 8-container implementation based on pilot results

---

## Next Steps After Pilot

### If Successful (Go Decision)
1. **Scale to Full Implementation**: Add remaining 5 MCP servers (TimescaleDB, Storage, Web Fetch, Playwright, n8n)
2. **Production Deployment**: Move to production-grade configuration with monitoring
3. **User Documentation**: Create usage guides and examples
4. **Performance Optimization**: Tune for production workloads

### If Issues Found (No-Go Decision)
1. **Fallback**: Return to current working mcp-server architecture
2. **Analysis**: Document specific issues preventing LiteLLM integration
3. **Alternative Approach**: Consider direct OpenWebUI integration or middleware solution
4. **Timeline Adjustment**: Reassess implementation approach and timeline

---

## Implementation Priority

### Phase 1 Focus: PostgreSQL Only
- **Rationale**: Database access is most critical capability
- **Success Criteria**: If PostgreSQL MCP works with LiteLLM, continue
- **Fallback**: If PostgreSQL fails, abort pilot and reassess approach

### Phase 2 Focus: Add Filesystem
- **Rationale**: File operations are second most important
- **Success Criteria**: Both PostgreSQL and filesystem tools working
- **Validation Point**: Confirm tool interaction patterns work

### Phase 3 Focus: Complete with Monitoring
- **Rationale**: Monitoring completes essential toolset
- **Success Criteria**: All 3 servers working together harmoniously
- **Go/No-Go**: Decision point for full 8-container implementation

---

**Timeline**: 5 days for pilot implementation and validation
**Outcome**: Go/No-Go decision for full MCP architecture with 8 containers
**Success Definition**: All 3 pilot tools accessible via LiteLLM with confirmed OpenWebUI integration

*This pilot validates the core LiteLLM + MCP integration before committing to full implementation.*
