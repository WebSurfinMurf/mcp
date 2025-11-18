# Direct MCP Registration Guide

## Purpose
Use this guide to register MCP services with MCP clients (Claude Code CLI, Codex CLI, Open-WebUI). **Important discovery**: Claude Code CLI and Codex CLI use different transport mechanisms and require different registration approaches.

## Supported MCP Clients & Transport Methods
- **Claude Code CLI**:
  - ✅ **stdio transport** (RECOMMENDED): Direct Python process execution
  - ✅ **SSE transport**: HTTP Server-Sent Events (legacy method)
- **Codex CLI**:
  - ✅ **stdio transport** (ONLY): Direct Python process execution
  - ❌ **SSE transport**: NOT supported
- **Open-WebUI**: MCP integration (implementation TBD)

## Prerequisites
- For **stdio transport**: Python bridge scripts must be available for each service
- For **SSE transport**: MCP service container must expose its SSE endpoint on the host
- You are running the CLI on `LinuxServer` or can reach `127.0.0.1` from your workstation
- Claude CLI is at least v1.0.54 (for SSE support)
- Codex CLI with MCP support

## Current MCP Services Available

### Legacy Services (Already Deployed)
| Service | Port | SSE Endpoint | Purpose |
|---------|------|--------------|---------|
| postgres-direct | 48010 | `http://127.0.0.1:48010/sse` | PostgreSQL operations |
| fetch-direct | 9072 | `http://127.0.0.1:9072/fetch/sse` | Web fetching |

### New Services (From Containerization Plan)
| Service | Port | SSE Endpoint | Purpose |
|---------|------|--------------|---------|
| filesystem | 9073 | `http://127.0.0.1:9073/sse` | File operations |
| n8n | 9074 | `http://127.0.0.1:9074/sse` | Workflow automation |
| playwright | 9075 | `http://127.0.0.1:9075/sse` | Browser automation |
| minio | 9076 | `http://127.0.0.1:9076/sse` | S3/Object storage |
| timescaledb | 48011 | `http://127.0.0.1:48011/sse` | TimescaleDB operations |

## Registration Commands

### Recommended Method: stdio Transport (Works for Both CLI Tools)

**✅ RECOMMENDED: Use stdio transport for both Claude Code CLI and Codex CLI**

#### All Services - stdio Registration
```bash
# Core services
claude mcp add postgres python3 /home/administrator/projects/mcp/postgres/postgres-mcp-stdio.py --scope user
claude mcp add timescaledb python3 /home/administrator/projects/mcp/timescaledb/mcp-bridge.py --scope user

# File and web services
claude mcp add filesystem python3 /home/administrator/projects/mcp/filesystem/mcp-bridge.py --scope user
claude mcp add playwright python3 /home/administrator/projects/mcp/playwright/mcp-bridge.py --scope user

# Storage and workflow services
claude mcp add minio python3 /home/administrator/projects/mcp/minio/mcp-bridge.py --scope user
claude mcp add n8n python3 /home/administrator/projects/mcp/n8n/mcp-bridge.py --scope user

# Legacy fetch service (if available)
# claude mcp add fetch python3 /home/administrator/projects/mcp/fetch/mcp-bridge.py --scope user
```

#### Codex CLI Registration (Identical Commands)
```bash
# Core services
codex mcp add postgres python3 /home/administrator/projects/mcp/postgres/postgres-mcp-stdio.py
codex mcp add timescaledb python3 /home/administrator/projects/mcp/timescaledb/mcp-bridge.py

# File and web services
codex mcp add filesystem python3 /home/administrator/projects/mcp/filesystem/mcp-bridge.py
codex mcp add playwright python3 /home/administrator/projects/mcp/playwright/mcp-bridge.py

# Storage and workflow services
codex mcp add minio python3 /home/administrator/projects/mcp/minio/mcp-bridge.py
codex mcp add n8n python3 /home/administrator/projects/mcp/n8n/mcp-bridge.py
```

### Legacy Method: SSE Transport (Claude Code CLI Only)

**⚠️ LEGACY: SSE transport only works with Claude Code CLI, not Codex CLI**

```bash
# Claude Code CLI - SSE transport (not recommended)
claude mcp add postgres-direct http://127.0.0.1:48010/sse --transport sse --scope user
claude mcp add fetch http://127.0.0.1:9072/fetch/sse --transport sse --scope user
claude mcp add filesystem http://127.0.0.1:9073/sse --transport sse --scope user
claude mcp add n8n http://127.0.0.1:9074/sse --transport sse --scope user
claude mcp add playwright http://127.0.0.1:9075/sse --transport sse --scope user
claude mcp add minio http://127.0.0.1:9076/sse --transport sse --scope user
claude mcp add timescaledb http://127.0.0.1:48011/sse --transport sse --scope user
```

### Key Registration Differences
- **stdio transport**: Works with both Claude Code CLI and Codex CLI
- **SSE transport**: Only works with Claude Code CLI, not Codex CLI
- **Bridge scripts**: Required for stdio transport, located in each service directory
- **Default transport**: Claude Code CLI defaults to stdio (no `--transport` flag needed)

## One-Time Cleanup (Optional)
If you previously used central proxy entries, remove them to avoid conflicts:

### Claude Code CLI
```bash
claude mcp remove postgres-proxy --scope user
claude mcp remove fetch-proxy --scope user
```

### Codex CLI
```bash
codex mcp remove postgres-proxy
codex mcp remove fetch-proxy
```

## Verification Steps

### 1. Health Check Endpoints
Test that each service responds correctly:
```bash
# Test with proper SSE headers
curl -i -H "Accept: text/event-stream" http://127.0.0.1:9073/sse
curl -i -H "Accept: text/event-stream" http://127.0.0.1:9074/sse
curl -i -H "Accept: text/event-stream" http://127.0.0.1:9075/sse
curl -i -H "Accept: text/event-stream" http://127.0.0.1:9076/sse
curl -i -H "Accept: text/event-stream" http://127.0.0.1:48011/sse

# Legacy services
curl -i -H "Accept: text/event-stream" http://127.0.0.1:48010/sse
curl -i -H "Accept: text/event-stream" http://127.0.0.1:9072/fetch/sse
```

Expected response: HTTP 200 with `content-type: text/event-stream` and SSE data.

### 2. Authentication Testing (If Required)
Some services may require bearer tokens:
```bash
# Test with authentication header
curl -i -H "Authorization: Bearer $MCP_BEARER_TOKEN" -H "Accept: text/event-stream" http://127.0.0.1:9076/sse
```

### 3. CLI Registration Verification

#### Claude Code CLI (stdio transport)
```bash
claude mcp list
```
Expected output:
```
filesystem: python3 /home/administrator/projects/mcp/filesystem/mcp-bridge.py - ✓ Connected
n8n: python3 /home/administrator/projects/mcp/n8n/mcp-bridge.py - ✓ Connected
playwright: python3 /home/administrator/projects/mcp/playwright/mcp-bridge.py - ✓ Connected
minio: python3 /home/administrator/projects/mcp/minio/mcp-bridge.py - ✓ Connected
timescaledb: python3 /home/administrator/projects/mcp/timescaledb/mcp-bridge.py - ✓ Connected
postgres: python3 /home/administrator/projects/mcp/postgres/postgres-mcp-stdio.py - ✓ Connected
```

#### Codex CLI (stdio transport)
```bash
codex mcp list
```
Expected output:
```
Name         Command  Args                                                             Env
filesystem   python3  /home/administrator/projects/mcp/filesystem/mcp-bridge.py        -
minio        python3  /home/administrator/projects/mcp/minio/mcp-bridge.py             -
n8n          python3  /home/administrator/projects/mcp/n8n/mcp-bridge.py               -
playwright   python3  /home/administrator/projects/mcp/playwright/mcp-bridge.py        -
postgres     python3  /home/administrator/projects/mcp/postgres/postgres-mcp-stdio.py  -
timescaledb  python3  /home/administrator/projects/mcp/timescaledb/mcp-bridge.py       -
```

### 4. Tool Availability Test
In a CLI session:
- **Claude Code**: Run `/mcp` to see available tools
- **Codex**: Test tool availability according to Codex documentation

## Authentication Requirements

### Services Requiring Authentication
Based on upstream MCP server requirements:
- **TimescaleDB**: Database connection string (automatic via environment)
- **MinIO**: S3 access keys (automatic via environment)
- **n8n**: API key (if required by upstream)
- **Filesystem**: No authentication
- **Playwright**: No authentication

### Authentication Environment Setup
Authentication is handled via environment files in deployment. If manual token configuration is needed:

1. Check service documentation for token requirements
2. Store tokens in appropriate secrets files
3. Restart containers to load new environment variables

## Network Architecture

### Security Model
All MCP services use dedicated networks for isolation:
```
MCP Client (CLI) ──── 127.0.0.1:{port} ──── MCP Container ──── Service Network ──── Backend Service
```

### Network Isolation
- **filesystem, playwright**: Standalone (no backend dependencies)
- **timescaledb**: postgres-net → TimescaleDB
- **minio**: minio-net → MinIO
- **n8n**: n8n-net → n8n

This ensures MCP services only access what they need, not underlying infrastructure.

## Common Errors & Fixes

### Connection Issues (stdio transport - Recommended)
- **`Failed to connect`**:
  - Check bridge script exists and is executable: `ls -la /home/administrator/projects/mcp/{service}/mcp-bridge.py`
  - Test bridge script manually: `echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1}' | python3 /home/administrator/projects/mcp/{service}/mcp-bridge.py`
- **Python import errors**: Check required dependencies are installed
- **Bridge script errors**: Check container is running: `docker ps | grep mcp-{service}`
- **Codex vs Claude CLI compatibility**: Both use identical stdio commands now

### Connection Issues (SSE transport - Legacy)
- **`Failed to connect`**: Check container is running with `docker ps | grep mcp-{service}`
- **Wrong transport type**: Ensure correct flag (`--transport sse` for Claude Code CLI only)
- **Port conflicts**: Verify port is bound and not in use by another service
- **Network access**: Ensure service bound to `127.0.0.1` not `localhost`
- **Codex CLI incompatibility**: Codex CLI does NOT support SSE transport

### Authentication Issues
- **403/401 responses**: Check if service requires bearer token
- **Token missing**: Verify environment file has correct authentication variables
- **Token expired**: Check token rotation requirements for the backend service

### Service-Specific Issues
- **Filesystem**: Check volume mounts in docker-compose.yml
- **Database services**: Verify backend database is running and accessible
- **n8n**: Confirm n8n API is accessible and API key is valid
- **MinIO**: Verify S3 credentials and endpoint accessibility

### CLI-Specific Issues
- **Claude Code**: Default back to stdio means missing `--transport sse`
- **Codex**: Registration syntax differs - use `--type sse --url` format
- **Configuration persistence**: Claude uses `$HOME/projects/.claude/`, Codex may use different config

## Troubleshooting Commands

### Container Status
```bash
# Check MCP containers are running
docker ps | grep mcp-

# Check specific container logs
docker logs mcp-filesystem
docker logs mcp-n8n
docker logs mcp-playwright
docker logs mcp-minio
docker logs mcp-timescaledb
```

### Network Connectivity
```bash
# Test container can reach backend service
docker exec mcp-minio ping minio
docker exec mcp-n8n ping n8n
docker exec mcp-timescaledb ping timescaledb

# Check networks exist
docker network ls | grep -E "(minio-net|n8n-net|postgres-net)"
```

### Service Health
```bash
# Check backend services are running
docker ps | grep -E "(minio|n8n|timescaledb)"

# Test backend service APIs
curl -i http://minio:9000/health  # (from within minio-net)
curl -i http://n8n:5678/healthz   # (from within n8n-net)
```

## Related Files & Documentation
- **Deployment Plans**: `projects/mcp/PLAN.md` - Complete implementation plan
- **Service Configs**: `projects/mcp/{service}/docker-compose.yml` - Individual service definitions
- **Environment Files**: `secrets/mcp-{service}.env` - Authentication and configuration
- **Service Documentation**: `projects/mcp/{service}/CLAUDE.md` - Per-service documentation
- **CLI Configuration**:
  - Claude Code: `$HOME/projects/.claude/` (project scope)
  - Codex: Check Codex documentation for config location

## Port Reference Quick Guide
```
48010 - postgres-direct (legacy)
48011 - timescaledb (new)
9072  - fetch-direct (legacy)
9073  - filesystem (new)
9074  - n8n (new)
9075  - playwright (new)
9076  - minio (new)
```

## Lessons Learned - Complete MCP Implementation (2025-01-27)

### Critical Discovery: Codex CLI Transport Requirements

**Issue**: Initial documentation incorrectly assumed Codex CLI supported direct SSE URLs like Claude Code CLI.

**Reality**: Codex CLI expects to launch MCP servers as stdio processes, not connect to existing HTTP endpoints.

**Solution**: Bridge script pattern that converts stdio ↔ HTTP communication.

### Bridge Script Architecture

**Required for each MCP service with Codex CLI:**
```python
#!/usr/bin/env python3
# Translates stdin/stdout JSON-RPC ↔ HTTP MCP endpoint
# Located at: /home/administrator/projects/mcp/{service}/mcp-bridge.py

import json, sys, requests, asyncio

async def handle_request(request_data):
    response = requests.post("http://127.0.0.1:{port}/mcp", json=request_data)
    return response.json()

# stdio loop: read JSON-RPC from stdin, forward to HTTP, return via stdout
```

### MCP Protocol Implementation Gotchas

1. **Pydantic ID Field Validation**
   - **Issue**: FastAPI server expected `id` as string, Codex sends integer
   - **Fix**: Use `Union[str, int]` in Pydantic models for `id` field

2. **Missing Initialize Method**
   - **Issue**: Codex sends `initialize` method first, server had no handler
   - **Fix**: Added proper MCP initialize response with capabilities

3. **Path Handling Complexity**
   - **Issue**: Codex sends absolute paths (`/home/administrator/projects/...`)
   - **Container**: Files mounted at `/workspace`
   - **Fix**: Path translation logic to handle both absolute and relative paths

### Container Configuration Lessons

1. **File Permissions**
   - **Issue**: Non-root user couldn't access mounted volumes
   - **Fix**: Run container as root (`user: "0:0"`) for file access

2. **Symlink Handling**
   - **Issue**: Broken symlinks in workspace caused crashes
   - **Fix**: Graceful error handling with try/catch for stat() operations

3. **Volume Mount Strategy**
   - **Working**: `/home/administrator/projects:/workspace:ro`
   - **Security**: Read-only workspace, write-only temp directory

### Testing & Verification Process

**Essential steps for each MCP service:**
1. **Container Health**: `docker ps | grep mcp-{service}`
2. **HTTP Endpoints**: `curl http://127.0.0.1:{port}/health`
3. **MCP Protocol**: Test initialize and tools/list via bridge
4. **Codex Integration**: Register and test `/mcp` command
5. **Functional Testing**: Use actual tools in Codex session

### Documentation Impact

**Update Requirements for Future Services:**
- Bridge script must be created for each service
- Registration commands differ between CLI tools
- Path handling patterns established for workspace access
- Error handling patterns for graceful degradation

### Success Pattern Template

**For each new MCP service:**
1. **HTTP MCP Server**: FastAPI with proper MCP protocol
2. **Bridge Script**: stdio ↔ HTTP translator for Codex
3. **Container Setup**: Proper permissions and volume mounts
4. **Path Handling**: Support both absolute and relative paths
5. **Error Handling**: Graceful symlink and permission failures
6. **Testing Protocol**: Full end-to-end verification

**Registry Commands Pattern:**
```bash
# Claude Code CLI (direct SSE)
claude mcp add {service} http://127.0.0.1:{port}/sse --transport sse --scope user

# Codex CLI (via bridge)
codex mcp add {service} python3 /home/administrator/projects/mcp/{service}/mcp-bridge.py
```

### Complete Project Results (2025-01-27)

**5 MCP Services Successfully Deployed:**
- ✅ **filesystem** (9073) - 4 file operation tools
- ✅ **playwright** (9075) - 6 browser automation tools
- ✅ **timescaledb** (48011) - 6 database query tools
- ✅ **minio** (9076) - 9 S3/object storage tools
- ✅ **n8n** (9074) - 6 workflow automation tools

**All services registered and working in Codex CLI**

### Time Investment Analysis

**Phase 1 (filesystem + playwright): ~6 hours**
- Filesystem: 4 hours (including discovery of Codex requirements)
- Playwright: 2 hours (using established patterns)

**Phase 2 (timescaledb): ~3 hours**
- SSE-only service investigation: 1 hour
- Custom FastAPI replacement: 1.5 hours
- Bridge script and testing: 30 minutes

**Phase 3 (minio + n8n): ~2.5 hours**
- MinIO: 1.5 hours (S3 integration complexity)
- n8n: 1 hour (API client implementation)

**Total Project Time: ~11.5 hours**

**Key Time Savers Developed:**
- Bridge script template (reusable across all services)
- FastAPI MCP server template (with both SSE + HTTP POST)
- Container configuration patterns
- Network isolation strategies
- Path handling for workspace mounting
- Health check and verification procedures

**Future Service Estimate: 45-60 minutes** (using all established patterns)

### 🚨 Major Discovery: Transport Protocol Requirements (2025-01-27)

**Critical Finding**: Claude Code CLI and Codex CLI had fundamental transport protocol incompatibility that required investigation and resolution.

### Original Problem
- **Claude Code CLI**: Was configured to use SSE transport (`http://127.0.0.1:port/sse`)
- **Codex CLI**: Uses stdio transport (`python3 /path/to/script.py`)
- **Result**: Services worked for Codex but failed for Claude Code CLI

### Root Cause Analysis
**Initial hypothesis (incorrect)**: Concurrent connection limits
**Actual root cause**: Transport protocol mismatch

**Transport Compatibility Discovery:**
```
CLI Tool        | SSE Transport | stdio Transport
----------------|---------------|----------------
Claude Code CLI | ✅ Supported  | ✅ Supported (DEFAULT)
Codex CLI       | ❌ NOT Supported | ✅ Only Method
```

### Solution Implementation
**✅ Unified stdio Approach**: Both CLI tools now use identical registration commands

**Before (incompatible):**
```bash
# Claude Code CLI (SSE)
claude mcp add filesystem http://127.0.0.1:9073/sse --transport sse --scope user

# Codex CLI (stdio)
codex mcp add filesystem python3 /home/administrator/projects/mcp/filesystem/mcp-bridge.py
```

**After (compatible):**
```bash
# Both CLI tools use identical commands
claude mcp add filesystem python3 /home/administrator/projects/mcp/filesystem/mcp-bridge.py --scope user
codex mcp add filesystem python3 /home/administrator/projects/mcp/filesystem/mcp-bridge.py
```

### Key Discovery Points

1. **Claude Code CLI Default Transport**: stdio (not SSE)
   - No `--transport` flag needed for stdio (it's the default)
   - SSE transport requires explicit `--transport sse` flag

2. **Codex CLI Transport Support**: stdio only
   - Cannot connect to HTTP endpoints directly
   - Requires process execution for MCP protocol

3. **Bridge Script Pattern**: Required for stdio compatibility
   - Each service needs `mcp-bridge.py` in its directory
   - Bridge translates stdin/stdout JSON-RPC ↔ HTTP API calls

### Transport Comparison Matrix

**SSE Transport (Legacy):**
- ✅ Claude Code CLI: Supported
- ❌ Codex CLI: Not supported
- ⚠️ Complexity: Dual registration methods

**stdio Transport (Recommended):**
- ✅ Claude Code CLI: Supported (default)
- ✅ Codex CLI: Supported (only method)
- ✅ Simplicity: Single registration method for both tools

### Implementation Benefits
- **Unified commands**: Same registration for both CLI tools
- **Simplified maintenance**: Single bridge script per service
- **Better compatibility**: Works with current and future MCP clients
- **Reduced confusion**: One documented method instead of two

### Discovery: Existing vs Custom MCP Services

**Existing "Out-of-the-Box" Services:**
- **mcp-postgres** (port 48010): SSE-only transport
- **mcp-fetch-bridge** (port 9072): Custom protocol, not standard MCP

**Key Findings:**
1. **SSE-only services cannot be directly registered with Codex CLI**
   - Codex requires stdio processes, not HTTP endpoints
   - Need bridge scripts even for existing services

2. **Updated Transport Compatibility Matrix:**
   ```
   Service Type        | Claude Code CLI | Codex CLI
   -------------------|-----------------|------------
   SSE Endpoint       | ✅ SSE Flag     | ❌ Need Bridge
   stdio Bridge       | ✅ Default      | ✅ Direct
   Custom FastAPI     | ✅ Both Methods | ✅ Bridge Script
   ```

3. **Custom Implementation Benefits:**
   - **Dual Transport**: Both SSE (legacy) and stdio (recommended) support
   - **Full Control**: Custom tools, authentication, error handling
   - **Documentation**: Complete service documentation and examples
   - **Health Checks**: Standard health endpoints for monitoring

**Recommendation**: Use stdio transport with bridge scripts for maximum CLI compatibility.

### Network Architecture Discoveries

**Container Communication Patterns:**
```
Phase 1: Standalone Services
├── filesystem: Direct file access (no network deps)
└── playwright: Direct browser automation (no network deps)

Phase 2: Single Network Dependency
└── timescaledb: postgres-net → TimescaleDB container

Phase 3: Complex Network Dependencies
├── minio: minio-net → MinIO container
└── n8n: n8n-net → n8n + n8n-worker containers
```

**Network Security Benefits:**
- MCP services isolated in dedicated networks
- No access to broader infrastructure
- Principle of least privilege (only access required services)
- Easy to monitor and audit connections

### Authentication Patterns Established

**Service Authentication Strategy:**
- **Environment-based**: Credentials via docker environment variables
- **Network-level**: Services only accessible via dedicated networks
- **No Token Rotation**: Long-lived credentials for stable operation
- **Read-only Defaults**: Database and API access limited by default

**Security Model:**
```
Host (CLI) → 127.0.0.1:port → MCP Container → Service Network → Backend
```
- All MCP endpoints bound to localhost only
- No external network exposure
- Network isolation prevents lateral access

## Maintenance Notes
- Update this document when new MCP services are added
- Verify port assignments don't conflict with existing services
- Test registration commands when CLI tools are updated
- Document any authentication requirement changes
- Update network architecture if service dependencies change
- **Bridge scripts must be created for all new services targeting Codex CLI**

---
*Last Updated: 2025-01-27 (Complete Implementation)*
*Purpose: Centralized guide for direct MCP registration across multiple CLI clients*
*Related: MCP Containerization Plan (PLAN.md) - 100% Complete*
*Project Status: ✅ All 5 planned MCP services successfully deployed and tested*