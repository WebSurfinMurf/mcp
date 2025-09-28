# MCP Filesystem Service

## Quick Start

### Status
✅ **Deployed and Operational** (2025-01-27)

### Access
- **Port**: 127.0.0.1:9073
- **Health**: http://127.0.0.1:9073/health
- **SSE Endpoint**: http://127.0.0.1:9073/sse

### Registration

#### Codex CLI
```bash
codex mcp add filesystem python3 /home/administrator/projects/mcp/filesystem/mcp-bridge.py
```

#### Claude Code CLI
```bash
claude mcp add filesystem http://127.0.0.1:9073/sse --transport sse --scope user
```

### Available Tools
1. `list_files` - List directory contents
2. `read_file` - Read file contents (workspace)
3. `write_file` - Write files (temp directory only)
4. `get_file_info` - Get file/directory metadata

### Verification
```bash
# Health check
curl http://127.0.0.1:9073/health

# List available tools
curl -X POST http://127.0.0.1:9073/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": "1"}'

# Container status
docker ps | grep mcp-filesystem
```

### Management
```bash
# Deploy/restart
cd /home/administrator/projects/mcp/filesystem
./deploy.sh

# Logs
docker logs mcp-filesystem

# Stop
docker stop mcp-filesystem
```

## File Access
- **Read**: Full `/home/administrator/projects` (read-only)
- **Write**: `/tmp` directory only (security)
- **Workspace**: Available as `/workspace` in container

For detailed documentation, see `CLAUDE.md`.