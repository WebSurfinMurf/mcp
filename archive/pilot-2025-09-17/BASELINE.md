# MCP Pilot Implementation - Baseline State

**Date**: 2025-09-16
**Time**: Phase 1 Environment Preparation
**Goal**: Document starting point for 3-tool MCP pilot

---

## Environment State Before Pilot

### MCP Infrastructure
- **Previous MCP Server**: Stopped and clear (no containers running)
- **Container Status**: No "mcp" containers running
- **Networks**: Existing networks available (postgres-net, observability-net)
- **Port Availability**: 8080, 8081, 8082 available for pilot containers

### Existing Infrastructure (Unchanged)
- **PostgreSQL**: Running on postgres:5432 (admin/Pass123qp)
- **Loki**: Running on loki:3100 (logs)
- **Netdata**: Running on netdata:19999 (metrics)
- **LiteLLM**: Running on litellm:4000 (17 AI models configured)
- **OpenWebUI**: Running on open-webui.ai-servicers.com

### LiteLLM Current Configuration
- **Model Count**: 17 AI models (GPT-5, Claude Opus 4.1, Gemini 2.5, etc.)
- **Config File**: /home/administrator/projects/litellm/config.yaml
- **Status**: Operational, ready for Smart Router tool additions

---

## Pilot Implementation Plan

### Selected MCP Servers
1. **PostgreSQL**: HenkDz/postgresql-mcp-server (17 tools)
2. **Filesystem**: Official modelcontextprotocol/servers (with HTTP adapter)
3. **Monitoring**: Custom Loki/Netdata wrapper (4 tools)

### Target Architecture
```
OpenWebUI → LiteLLM Smart Router → Tool "Models" → MCP Containers
                                 ↓
                      tool-postgresql (8080)
                      tool-filesystem (8081)
                      tool-monitoring (8082)
```

### Success Criteria
- All 3 containers healthy and responding
- LiteLLM discovers tool "models" correctly
- HTTP proxy routing works end-to-end
- OpenWebUI can access tools through LiteLLM

---

## Directory Structure Created

```
/home/administrator/projects/mcp/pilot/
├── docker-compose.yml          # Master compose file
├── BASELINE.md                 # This file
├── postgresql/                 # Phase 2 implementation
├── filesystem/                 # Phase 3 implementation
└── monitoring/                 # Phase 4 implementation
```

---

## Network Configuration

### New Network: mcp-pilot
- **Subnet**: 172.30.0.0/24
- **Purpose**: Isolated network for pilot containers
- **External Networks**: postgres-net, observability-net

### Port Mappings
- **8080**: mcp-postgresql (PostgreSQL tools)
- **8081**: mcp-filesystem (File operations)
- **8082**: mcp-monitoring (System monitoring)

---

## Next Steps

**Phase 2**: Implement PostgreSQL MCP server using HenkDz/postgresql-mcp-server
- Clone repository and analyze 17 available tools
- Create Dockerfile and HTTP adapter if needed
- Test connectivity to existing PostgreSQL instance

**Success Checkpoint**: PostgreSQL container healthy and tools discoverable

---

*Baseline documented at start of 5-day pilot implementation*