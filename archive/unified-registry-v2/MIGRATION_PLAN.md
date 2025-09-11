# MCP v2 Architecture Migration Plan

**Date**: 2025-09-08  
**Objective**: Migrate all MCP services to the new dual-mode v2 architecture for consistency and maintainability

## Current State Analysis

### 1. Claude Code MCP Servers (3 active)
Currently using direct Docker/npx commands in `~/.config/claude/mcp_servers.json`:
- **mcp-filesystem** - Docker container with volume mount
- **mcp-postgres** - Docker container with postgres-net
- **mcp-github** - npx command with GitHub token

### 2. LiteLLM Integration (via SSE proxy)
Currently using SSE proxy at port 8585 in `litellm/config.yaml`:
- 7 MCP services via SSE endpoints
- Going through `mcp-proxy-sse` container
- Mock middleware at port 4001

### 3. Unified Registry (Phase 1)
Already built adapters at `/home/administrator/projects/mcp/unified-registry/`:
- 7 services, 24 tools
- Claude adapter working
- LiteLLM adapter pending

## Migration Benefits

### Why Migrate Everything to v2?

1. **Consistency** - Single architecture for all services
2. **Security** - Comprehensive validation and allowlisting
3. **Maintainability** - One codebase per service, not multiple adapters
4. **Flexibility** - Easy to add WebSocket, gRPC later
5. **Professional** - Pydantic validation, structured logging, connection pooling
6. **Deployment** - Single `deploy.sh` script for everything

## Migration Strategy

### Phase 1: Complete v2 Services (Week 1)

#### 1.1 Implement Remaining Core Services
```
Priority Order:
1. ✅ PostgreSQL (completed)
2. ⏳ Filesystem 
3. ⏳ GitHub
4. ⏳ Monitoring
5. ⏳ N8n
6. ⏳ TimescaleDB
7. ⏳ Playwright
```

#### 1.2 Service Implementation Template
Each service needs:
- Pydantic models (`{service}_models.py`)
- Service class (`mcp_{service}.py`)
- Configuration (`config/{service}.ini`)
- Security settings (allowed paths, operations)

### Phase 2: Claude Code Migration (Day 2)

#### 2.1 Backup Current Configuration
```bash
cp ~/.config/claude/mcp_servers.json ~/.config/claude/mcp_servers.json.backup-v1
```

#### 2.2 Create v2 Configuration
```json
{
  "mcpServers": {
    "postgres-v2": {
      "command": "/home/administrator/projects/mcp/unified-registry-v2/deploy.sh",
      "args": ["run", "postgres", "stdio"],
      "env": {
        "DATABASE_URL": "postgresql://admin:Pass123qp@localhost:5432/postgres"
      }
    },
    "filesystem-v2": {
      "command": "/home/administrator/projects/mcp/unified-registry-v2/deploy.sh",
      "args": ["run", "filesystem", "stdio"]
    },
    "github-v2": {
      "command": "/home/administrator/projects/mcp/unified-registry-v2/deploy.sh",
      "args": ["run", "github", "stdio"],
      "env": {
        "GITHUB_TOKEN": "ghp_..."
      }
    }
  }
}
```

#### 2.3 Gradual Migration
1. Add v2 services alongside v1
2. Test each v2 service
3. Remove v1 services once confirmed
4. Update documentation

### Phase 3: LiteLLM Migration (Day 3)

#### 3.1 Deploy v2 Services in SSE Mode
```bash
# Start all services in SSE mode
./deploy.sh run postgres sse --port 8001 &
./deploy.sh run filesystem sse --port 8002 &
./deploy.sh run github sse --port 8003 &
./deploy.sh run monitoring sse --port 8004 &
./deploy.sh run n8n sse --port 8005 &
./deploy.sh run timescaledb sse --port 8006 &
./deploy.sh run playwright sse --port 8007 &
```

#### 3.2 Update LiteLLM Config
Replace SSE proxy URLs with direct v2 endpoints:
```yaml
mcp_servers:
  postgres:
    transport: "http"
    url: "http://localhost:8001/rpc"
    description: "PostgreSQL database operations"
    
  filesystem:
    transport: "http"
    url: "http://localhost:8002/rpc"
    description: "File system operations"
```

#### 3.3 Update Middleware
Modify MCP middleware to use v2 JSON-RPC endpoints

### Phase 4: Cleanup (Day 4)

#### 4.1 Services to Remove
- `/home/administrator/projects/mcp/unified-registry/` (old adapter)
- `/home/administrator/projects/mcp/proxy-sse/` (no longer needed)
- Individual MCP service Docker containers

#### 4.2 Containers to Stop
```bash
docker stop mcp-proxy-sse
docker stop mcp-filesystem
docker stop mcp-postgres-stdio
docker stop mcp-fetch
docker stop mcp-timescaledb
```

#### 4.3 Archive Old Code
```bash
# Create archive of old implementation
tar -czf mcp-v1-archive.tar.gz \
  unified-registry/ \
  proxy-sse/ \
  filesystem/ \
  postgres/ \
  ...
```

## Implementation Checklist

### Week 1: Build Services
- [ ] Filesystem service with Pydantic models
- [ ] GitHub service with Pydantic models
- [ ] Monitoring service with Pydantic models
- [ ] N8n service with Pydantic models
- [ ] TimescaleDB service with Pydantic models
- [ ] Playwright service with Pydantic models

### Day 2: Claude Migration
- [ ] Backup current mcp_servers.json
- [ ] Create v2 configuration
- [ ] Test each service individually
- [ ] Update Claude configuration
- [ ] Verify all tools working

### Day 3: LiteLLM Migration
- [ ] Deploy services in SSE mode
- [ ] Update litellm/config.yaml
- [ ] Modify middleware for v2
- [ ] Test with Open WebUI
- [ ] Verify tool execution

### Day 4: Cleanup
- [ ] Stop old containers
- [ ] Archive old code
- [ ] Update documentation
- [ ] Remove unused dependencies
- [ ] Clean Docker images

## Service Implementation Priority

### High Priority (Core functionality)
1. **Filesystem** - Most used, file operations
2. **PostgreSQL** - Database operations ✅
3. **GitHub** - Version control

### Medium Priority (Automation)
4. **Monitoring** - Logs and metrics
5. **N8n** - Workflow automation

### Low Priority (Specialized)
6. **TimescaleDB** - Time-series data
7. **Playwright** - Browser automation

## Testing Strategy

### Unit Tests
Each service should have:
- Pydantic model validation tests
- Tool execution tests
- Error handling tests

### Integration Tests
- stdio mode with Claude Code
- SSE mode with curl/Postman
- End-to-end with Open WebUI

### Performance Tests
- Connection pooling efficiency
- Concurrent request handling
- Memory usage monitoring

## Risk Mitigation

### Rollback Plan
1. Keep v1 backups for 30 days
2. Document v1 configuration
3. Test rollback procedure
4. Maintain v1 Docker images

### Gradual Migration
1. Run v1 and v2 in parallel initially
2. Migrate one service at a time
3. Validate each service before proceeding
4. Keep detailed logs of migration

## Success Criteria

### Technical
- ✅ All 7 services implemented in v2
- ✅ Pydantic validation for all inputs
- ✅ Security allowlisting configured
- ✅ Both stdio and SSE modes working
- ✅ Connection pooling for databases

### Operational
- ✅ Single deploy.sh for all services
- ✅ Consistent logging and monitoring
- ✅ Comprehensive documentation
- ✅ Automated testing
- ✅ Clean removal of old code

### User Experience
- ✅ No service interruption
- ✅ Better error messages
- ✅ Faster response times
- ✅ More reliable execution
- ✅ Easier troubleshooting

## Timeline

### Week 1 (Current)
- Day 1: ✅ Base framework + PostgreSQL
- Day 2-5: Implement remaining 6 services
- Day 6-7: Testing and refinement

### Week 2
- Day 1-2: Claude Code migration
- Day 3-4: LiteLLM migration
- Day 5: Cleanup and documentation
- Day 6-7: Production deployment

## Conclusion

The v2 architecture is superior in every way:
- **Cleaner** - No complex adapters or proxies
- **Safer** - Comprehensive validation and security
- **Faster** - Direct execution, connection pooling
- **Simpler** - One way to do things
- **Professional** - Production-ready quality

By migrating everything to v2, we achieve consistency across the entire MCP infrastructure and set a solid foundation for future enhancements.

---
*"The best time to plant a tree was 20 years ago. The second best time is now."*
*Let's build this right, once and for all.*