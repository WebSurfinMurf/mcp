# MCP Filesystem Service

## 📋 Project Overview
Filesystem MCP service providing file system operations for MCP clients. Enables reading, writing, and listing files within the projects workspace through standardized MCP protocol.

## 🟢 Current State - ✅ Operational (2025-01-27)
- **Container**: mcp-filesystem (running, healthy)
- **Port**: 127.0.0.1:9073
- **SSE Endpoint**: http://127.0.0.1:9073/sse
- **Health Endpoint**: http://127.0.0.1:9073/health
- **Status**: Fully deployed and operational
- **Phase**: Phase 1 (Standalone) - ✅ Complete

## 📝 Recent Work & Changes

### Session: 2025-01-27
- **[Deployment]**: Custom MCP filesystem server implementation
  - Built custom FastAPI-based MCP server (gabrielmaialva33/mcp-filesystem not available)
  - Configured with 4 filesystem tools: list_files, read_file, write_file, get_file_info
  - Fixed container permissions for workspace access
  - Verified health, SSE, and MCP endpoints operational
  - Phase 1 implementation complete

## 🏗️ Architecture

### Container Configuration
- **Image**: Custom built from Python 3.11-slim
- **Container Name**: mcp-filesystem
- **Networks**: Default bridge (standalone, no dependencies)
- **User**: Root (for filesystem access)
- **Build**: Local Dockerfile with FastAPI server

### Port Configuration
- **Host Port**: 127.0.0.1:9073 (localhost-only)
- **Container Port**: 8000
- **Protocol**: HTTP (internal access only)

### Volume Mounts
- `/home/administrator/projects` → `/workspace` (read-only)
- `/tmp` → `/tmp` (read-write for temporary files)

### Dependencies
- None (standalone service)

## ⚙️ Configuration

### Environment File
- **Location**: `$HOME/projects/secrets/mcp-filesystem.env`
- **Permissions**: 600 (owner read/write only)
- **Variables**:
  - `MCP_SERVER_NAME=filesystem`
  - `WORKSPACE_PATH=/workspace`
  - `TEMP_PATH=/tmp`

### Docker Compose
- **File**: `/home/administrator/projects/mcp/filesystem/docker-compose.yml`
- **Build**: Local Dockerfile
- **Restart Policy**: unless-stopped
- **Health Check**: Every 30s via /health endpoint

## 🌐 Access & Management

### Endpoints
- **Health Check**: `curl http://127.0.0.1:9073/health`
- **SSE Endpoint**: `curl -H "Accept: text/event-stream" http://127.0.0.1:9073/sse`
- **MCP HTTP**: `curl -X POST http://127.0.0.1:9073/mcp -H "Content-Type: application/json" -d '{"jsonrpc": "2.0", "method": "tools/list", "id": "1"}'`

### MCP Tools Available
1. **list_files**: List files and directories in workspace
2. **read_file**: Read file contents from workspace (read-only)
3. **write_file**: Write files to temp directory (security limited)
4. **get_file_info**: Get file/directory metadata

### Registration Commands
```bash
# Codex CLI (via stdio bridge)
codex mcp add filesystem python3 /home/administrator/projects/mcp/filesystem/mcp-bridge.py

# Claude Code CLI (direct SSE)
claude mcp add filesystem http://127.0.0.1:9073/sse --transport sse --scope user
```

## 🔗 Integration Points

### File Access Patterns
- **Read Access**: Full workspace (/home/administrator/projects) read-only
- **Write Access**: Limited to temp directory (/tmp) for security
- **Workspace Structure**: Projects directory tree accessible for browsing and reading

### Security Model
- Localhost-only binding (127.0.0.1)
- No external network exposure
- Read-only workspace access
- Write operations restricted to temp directory

## 🛠️ Operations

### Deployment
```bash
cd /home/administrator/projects/mcp/filesystem
./deploy.sh
```

### Container Management
```bash
# Status check
docker ps | grep mcp-filesystem

# Logs
docker logs mcp-filesystem

# Restart
docker restart mcp-filesystem

# Shell access
docker exec -it mcp-filesystem /bin/bash
```

### Health Monitoring
```bash
# Health endpoint
curl http://127.0.0.1:9073/health

# Container health
docker inspect mcp-filesystem --format='{{.State.Health.Status}}'

# Test workspace access
docker exec mcp-filesystem ls -la /workspace
```

## 🔧 Troubleshooting

### Common Issues

#### Container Not Starting
- **Check**: Docker build logs: `docker logs mcp-filesystem`
- **Check**: Port conflicts: `netstat -tlnp | grep 9073`
- **Solution**: Verify no other service using port 9073

#### Permission Denied on Workspace
- **Symptom**: Cannot access /workspace directory
- **Cause**: Container user permissions
- **Solution**: Container runs as root (user: "0:0" in docker-compose.yml)

#### SSE Endpoint Timeout
- **Symptom**: SSE connection hangs or times out
- **Check**: Health endpoint responding: `curl http://127.0.0.1:9073/health`
- **Solution**: SSE is streaming - connection staying open is expected behavior

#### MCP Tools Not Listed
- **Test**: `curl -X POST http://127.0.0.1:9073/mcp -H "Content-Type: application/json" -d '{"jsonrpc": "2.0", "method": "tools/list", "id": "1"}'`
- **Expected**: 4 tools (list_files, read_file, write_file, get_file_info)
- **Solution**: Restart container if tools not available

### Log Analysis
```bash
# Real-time logs
docker logs -f mcp-filesystem

# Recent errors
docker logs mcp-filesystem 2>&1 | grep -i error

# Container events
docker events --filter container=mcp-filesystem
```

## 📋 Standards & Best Practices

### File Operations
- Always use relative paths for workspace operations
- Check file exists before reading
- Use appropriate encoding (default: utf-8)
- Limit write operations to temp directory

### MCP Protocol
- Follow JSON-RPC 2.0 specification
- Include proper error handling
- Use structured tool schemas
- Maintain consistent response formats

### Security
- No credential storage in this service
- Workspace is read-only for safety
- Temp directory for temporary file operations
- Localhost-only binding prevents external access

## 🔐 Backup & Security

### No Persistent Data
- Service is stateless
- No data backup required
- Configuration in git-tracked files

### Security Considerations
- Container has root access for file operations
- Workspace mounted read-only
- No network dependencies
- No authentication required (internal service)

### Monitoring
- Health check every 30s
- Docker health status integration
- Log rotation via Docker (10MB, 3 files)

## 🔄 Related Services

### Phase 1 Services (Standalone)
- ✅ **filesystem** (this service)
- ⏸️ **playwright** (port 9075) - Next implementation

### Future Integration
- Will integrate with Codex CLI for file operations
- No dependencies on other MCP services
- Foundation for file-based workflows

### MCP Infrastructure
- Part of Phase 1 (Standalone services)
- No network dependencies
- Direct SSE/HTTP integration

---
**Implementation**: Phase 1 Complete
**Status**: ✅ Operational
**Last Updated**: 2025-01-27
**Next**: Playwright MCP implementation