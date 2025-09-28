# PostgreSQL MCP Integration

## Project Overview

PostgreSQL MCP integration providing database access for AI agents through both SSE and stdio transports. Uses the official **crystaldba/postgres-mcp** server which supports advanced database operations including query optimization, health checks, and safe SQL execution.

## Current State

**Dual Transport Architecture:**
- **SSE Transport**: Existing container (`mcp-postgres`) on port 48010 for Claude Code CLI
- **stdio Transport**: Direct postgres-mcp runner for Codex CLI compatibility

**Status:** ✅ SSE container operational, stdio runner created, testing in progress

## Architecture

### SSE Transport (Existing)
```
Claude Code CLI → http://127.0.0.1:48010/sse → mcp-postgres container → postgres database
```

### stdio Transport (New)
```
Codex CLI → postgres-mcp-stdio.py → postgres-mcp (stdio mode) → postgres database
```

### Network Configuration
- **SSE Container**: Connected to default Docker network, exposed on host port 48010
- **stdio Mode**: Direct host execution, connects to postgres container via network
- **Database**: postgres:5432 (main PostgreSQL instance)

## Configuration

### Environment Files
- **SSE mode**: Configured via container environment variables
- **stdio mode**: Uses `DATABASE_URL` environment variable

### Database Connection
```bash
DATABASE_URL=postgresql://admin:Pass123qp@postgres:5432/postgres
```

### Container Details (SSE)
- **Image**: `crystaldba/postgres-mcp@sha256:dbbd346860d29f1543e991f30f3284bf4ab5f096d049ecc3426528f20b1b6e6b`
- **Container**: `mcp-postgres`
- **Port**: 48010 (SSE endpoint)
- **Health**: Available at `/sse` and `/messages/` endpoints

## Access & Management

### Claude Code CLI Registration
```bash
claude mcp add postgres-direct http://127.0.0.1:48010/sse --transport sse --scope user
```

### Codex CLI Registration (Recommended)
```bash
# Install postgres-mcp first
pip3 install --user postgres-mcp>=0.3.0

# Register stdio runner (main postgres instance)
codex mcp add postgres python3 /home/administrator/projects/mcp/postgres/postgres-mcp-stdio.py
```

### Codex CLI Registration (Legacy Bridge - Deprecated)
```bash
# Old hokey bridge approach - not recommended
codex mcp add postgres python3 /home/administrator/projects/mcp/postgres/mcp-bridge.py
```

### Direct Testing
```bash
# Test stdio mode directly
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1}' | python3 /home/administrator/projects/mcp/postgres/postgres-mcp-stdio.py

# Test SSE endpoint
curl -i -H "Accept: text/event-stream" http://127.0.0.1:48010/sse
```

## Integration Points

### Database Access
- **Target Database**: Main postgres instance (postgres:5432)
- **Credentials**: admin user with Pass123qp password
- **Access Mode**: Can be configured for read-only or full access
- **Connection Pool**: Managed by postgres-mcp server

### MCP Capabilities
Based on crystaldba/postgres-mcp features:
- Query execution with safety controls
- Database health analysis
- Index tuning recommendations
- Query plan explanation and optimization
- Schema intelligence for context-aware SQL generation
- Performance monitoring tools

### Transport Compatibility
| Client | Transport | Endpoint | Status |
|--------|-----------|----------|---------|
| Claude Code CLI | SSE | http://127.0.0.1:48010/sse | ✅ Working |
| Codex CLI | stdio | postgres-mcp-stdio.py | 🔄 Testing |
| Custom Bridge | stdio→SSE | mcp-bridge.py | ⚠️ Deprecated |

## Operations

### Container Management (SSE)
```bash
# Check status
docker ps | grep mcp-postgres

# View logs
docker logs mcp-postgres

# Restart if needed
docker restart mcp-postgres
```

### stdio Mode Management
```bash
# Setup
cd /home/administrator/projects/mcp/postgres
./setup.sh

# Verify installation
python3 -m postgres_mcp --help

# Test connection
python3 postgres-mcp-stdio.py
```

### Health Monitoring
```bash
# SSE endpoint health
curl -f http://127.0.0.1:48010/health

# Container health
docker exec mcp-postgres python3 -c "import psycopg2; print('DB OK')"

# stdio mode test
echo '{"jsonrpc":"2.0","method":"ping","id":1}' | python3 postgres-mcp-stdio.py
```

## Troubleshooting

### Common Issues

**SSE Transport Issues:**
- **Connection timeout**: Check container is running and port 48010 is accessible
- **No tools available**: Verify database connection and permissions
- **SSE stream errors**: Check container logs for authentication issues

**stdio Transport Issues:**
- **Module not found**: Run `pip3 install --user postgres-mcp`
- **Database connection failed**: Verify DATABASE_URL and network connectivity
- **Permission denied**: Check postgres user has required database privileges

**Database Connection Issues:**
- **Authentication failed**: Verify credentials in DATABASE_URL
- **Network unreachable**: Ensure postgres container is running and accessible
- **Too many connections**: Check connection pool settings and active connections

### Diagnostic Commands
```bash
# Check all MCP registrations
codex mcp list
claude mcp list

# Test database connectivity
docker exec postgres psql -U admin -d postgres -c "SELECT version();"

# Check network connectivity
docker exec mcp-postgres ping postgres

# Verify MCP server capabilities
docker logs mcp-postgres | grep -i "tool\|capability"
```

### Recovery Procedures
```bash
# Reset Codex registration
codex mcp remove postgres
codex mcp remove postgres-stdio
# Re-register with correct transport

# Restart SSE container
docker restart mcp-postgres

# Reinstall stdio dependencies
pip3 uninstall postgres-mcp
pip3 install --user postgres-mcp>=0.3.0
```

## Standards & Best Practices

### Security
- **Read-only mode**: Consider using restricted mode for production
- **Connection limits**: Monitor and limit concurrent connections
- **Credential management**: Store DATABASE_URL securely, avoid hardcoding
- **Network isolation**: Keep database access within Docker networks where possible

### Performance
- **Connection pooling**: Leverage postgres-mcp's built-in connection management
- **Query optimization**: Use postgres-mcp's index tuning and explain plan features
- **Resource monitoring**: Monitor database performance impact of MCP operations

### Maintenance
- **Regular updates**: Keep postgres-mcp package updated for security and features
- **Log rotation**: Monitor and rotate container logs to prevent disk space issues
- **Health checks**: Implement regular connectivity and performance health checks
- **Documentation**: Keep this file updated when configuration changes

## Related Projects

### Upstream
- **crystaldba/postgres-mcp**: https://github.com/crystaldba/postgres-mcp
- **Official MCP Specification**: https://modelcontextprotocol.io/

### Local Integration
- **Main postgres instance**: `/home/administrator/docker-compose.yml`
- **MCP containerization plan**: `/home/administrator/projects/mcp/PLAN.md`
- **Direct MCP registration guide**: `/home/administrator/projects/mcp/directmcp.md`

### Alternative Approaches
- **TBXark/mcp-proxy**: For SSE-to-stdio bridging (investigated but not needed)
- **Custom FastAPI MCP servers**: Pattern used for other services in this project

---

**Key Discovery:** crystaldba/postgres-mcp natively supports both SSE and stdio transports, eliminating the need for custom bridge scripts. The hokey SSE-to-stdio bridge approach (`mcp-bridge.py`) has been replaced with direct stdio execution (`postgres-mcp-stdio.py`).

**Transport Matrix:**
- **Claude Code CLI**: Direct SSE → Use existing container
- **Codex CLI**: Direct stdio → Use postgres-mcp-stdio.py runner
- **Bridge Scripts**: Deprecated → Use native transport support instead

**Next Steps:**
1. Test stdio runner with Codex CLI
2. Replace hokey bridge registration with stdio runner
3. Verify all postgres-mcp tools are available and functional
4. Document any transport-specific limitations or differences