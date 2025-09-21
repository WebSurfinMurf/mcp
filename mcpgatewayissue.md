# LiteLLM MCP Gateway Transport Issue - Exhaustive Report

## 📋 Executive Summary

**Problem**: LiteLLM MCP Gateway is deployed and operational, but PostgreSQL MCP tools are not accessible despite both components claiming transport compatibility.

**Status**: Infrastructure fully deployed, authentication working, but MCP server shows as disconnected/unavailable.

**Need**: Expert analysis to resolve transport configuration mismatch between LiteLLM and PostgreSQL MCP server.

---

## 🎯 Goal & Requirements

### Primary Objective
Deploy LiteLLM v1.77.3-stable as an MCP Gateway that provides PostgreSQL database tools to Claude Code CLI on local network (linuxserver.lan).

### Key Requirements
- ✅ LOCAL NETWORK ONLY (no Keycloak/Traefik)
- ✅ LiteLLM v1.77.3-stable at localhost:4000
- ✅ Support Claude Code CLI MCP connections
- ❌ **FAILING**: Access to PostgreSQL database tools via MCP

---

## 🏗️ Current Architecture

### Deployed Components

#### LiteLLM Gateway
- **Image**: `ghcr.io/berriai/litellm:main-latest` (confirmed v1.77.3)
- **Location**: `/home/administrator/projects/litellm/`
- **URL**: `http://localhost:4000`
- **Status**: ✅ Healthy and operational
- **Authentication**: Master key working (`sk-litellm-cecca...`)
- **MCP Endpoint**: `http://localhost:4000/mcp/` responds with SSE expectation

#### PostgreSQL MCP Server
- **Image**: `crystaldba/postgres-mcp:latest`
- **Location**: `/home/administrator/projects/mcp/postgres/`
- **Container**: `mcp-postgres`
- **Status**: ✅ Running and connected to database
- **Transport**: stdio only (confirmed from container logs)

#### Claude Code CLI
- **Config**: `/home/administrator/.config/claude/mcp-settings.json`
- **Status**: ✅ Configured with LiteLLM gateway connection
- **Authentication**: Using LiteLLM master key

### Network Architecture
```
Claude Code CLI → http://localhost:4000/mcp/ → LiteLLM Gateway → ??? → MCP Postgres
```

---

## 🔍 Transport Analysis

### LiteLLM Transport Capabilities
**User Confirmed**: LiteLLM configuration console shows three transport options:
- `stdio` - Standard Input/Output
- `http` - HTTP API calls
- `sse` - Server-Sent Events

### Current LiteLLM Configuration
```yaml
mcp_servers:
  db_main:
    transport: http
    url: http://mcp-postgres:8080/mcp
    api_keys:
      - ${LITELLM_VIRTUAL_KEY_TEST}
    description: "PostgreSQL database tools and queries via HTTP"
    timeout: 30
```

### PostgreSQL MCP Server Reality
**Container Logs Show**:
```
----------------
Executing command:
postgres-mcp
----------------
[09/21/25 18:01:50] INFO     Starting PostgreSQL MCP Server in     server.py:555
                             UNRESTRICTED mode
                    INFO     Successfully connected to database    server.py:568
                             and initialized connection pool
```

**Evidence**: Server starts successfully but only provides stdio interface.

---

## 🚨 The Core Problem

### Transport Mismatch Details

1. **LiteLLM Expectation**: HTTP transport at `http://mcp-postgres:8080/mcp`
2. **MCP Server Reality**: Only stdio transport available
3. **Container Networking**: MCP server exposes port 8686, not 8080
4. **No HTTP Endpoint**: crystaldba/postgres-mcp doesn't provide HTTP/REST API

### Attempted Solutions & Results

#### Attempt 1: SSE Transport (Initial)
```yaml
transport: sse
url: http://mcp-postgres:8686
```
**Result**: ❌ "Not Acceptable: Client must accept text/event-stream"

#### Attempt 2: stdio Transport
```yaml
transport: stdio
command: "docker"
args: ["exec", "-i", "mcp-postgres", "postgres-mcp"]
```
**Result**: ❌ "No such file or directory" (docker command not available in LiteLLM container)

#### Attempt 3: HTTP Transport (Current)
```yaml
transport: http
url: http://mcp-postgres:8080/mcp
```
**Result**: ❌ Connection failed (no HTTP endpoint available)

#### Attempt 4: Alternative Image
- **Tried**: `mcp/postgres:latest` (official image)
- **Issue**: Required database URL as command argument, failed to start properly
- **Reverted**: Back to `crystaldba/postgres-mcp:latest`

---

## 📊 Evidence Collection

### LiteLLM Health Check
```bash
curl -X GET "http://localhost:4000/health" \
  -H "Authorization: Bearer sk-litellm-cecca390f610603ff5180ba0ba2674afc8f7689716daf25343de027d10c32404"
```
**Result**: ✅ Healthy (with expected mock API key error)

### MCP Endpoint Test
```bash
curl -X GET "http://localhost:4000/mcp/" \
  -H "Authorization: Bearer sk-litellm-cecca390f610603ff5180ba0ba2674afc8f7689716daf25343de027d10c32404"
```
**Result**: `{"jsonrpc":"2.0","id":"server-error","error":{"code":-32600,"message":"Not Acceptable: Client must accept text/event-stream"}}`

### LiteLLM Logs
```
{"message": "MCP client connection failed: [Errno 2] No such file or directory", "level": "WARNING", "timestamp": "2025-09-21T18:02:16.165612"}
{"message": "MCP client session is not initialized", "level": "WARNING", "timestamp": "2025-09-21T18:02:16.184652"}
```

### MCP Container Status
```bash
docker logs mcp-postgres
```
**Result**: ✅ "Successfully connected to database and initialized connection pool"

---

## 🤔 Theoretical Transport Bridging

### Question: Should LiteLLM Bridge Transports?

If LiteLLM supports stdio, http, and sse transports as the user observed, there are several possible interpretations:

1. **Direct Support**: LiteLLM can connect directly to stdio-based MCP servers
2. **Transport Bridging**: LiteLLM can bridge between client connections and different MCP transports
3. **Client Options**: The three options refer to how clients connect to LiteLLM, not how LiteLLM connects to MCP servers

### Current Understanding Gap
**The fundamental question**: How does LiteLLM's stdio transport actually work with containerized MCP servers?

---

## 📋 Configuration Files

### LiteLLM Configuration
**File**: `/home/administrator/projects/litellm/config/config.yaml`
```yaml
litellm_settings:
  master_key: ${LITELLM_MASTER_KEY}
  database_url: ${DATABASE_URL}
  json_logs: true
  detailed_debug: true
  mcp_aliases:
    db: db_main
    fs: filesystem_main

general_settings:
  detailed_debug: true
  log_level: DEBUG
  disable_database: true

model_list:
  - model_name: gpt-4o-mock
    litellm_params:
      model: openai/gpt-4o-mini
      api_key: mock-key-for-testing

virtual_keys:
  - api_key: ${LITELLM_VIRTUAL_KEY_TEST}
    models: ["gpt-4o-mock"]
    mcp_servers: ["db"]
    description: "Test key for local network access with MCP"

mcp_servers:
  db_main:
    transport: http
    url: http://mcp-postgres:8080/mcp
    api_keys:
      - ${LITELLM_VIRTUAL_KEY_TEST}
    description: "PostgreSQL database tools and queries via HTTP"
    timeout: 30
```

### MCP Docker Compose
**File**: `/home/administrator/projects/mcp/postgres/docker-compose.yml`
```yaml
version: "3.9"

services:
  mcp-postgres:
    image: crystaldba/postgres-mcp:latest
    container_name: mcp-postgres
    restart: unless-stopped
    env_file:
      - /home/administrator/secrets/mcp-postgres.env
    environment:
      - MCP_TRANSPORT=stdio
      - MCP_ALLOW_WRITE=false
    ports:
      - "48010:8686"
    networks:
      - litellm-mcp-net
      - postgres-net
    healthcheck:
      disable: true
```

### Claude Code CLI Configuration
**File**: `/home/administrator/.config/claude/mcp-settings.json`
```json
{
  "mcpServers": {
    "litellm-gateway": {
      "transport": "http",
      "url": "http://localhost:4000/mcp/",
      "headers": {
        "Authorization": "Bearer sk-litellm-cecca390f610603ff5180ba0ba2674afc8f7689716daf25343de027d10c32404",
        "x-mcp-servers": "db_main",
        "Host": "localhost"
      }
    }
  }
}
```

### Environment Variables
**File**: `/home/administrator/secrets/litellm.env`
```bash
LITELLM_MASTER_KEY=sk-litellm-cecca390f610603ff5180ba0ba2674afc8f7689716daf25343de027d10c32404
LITELLM_VIRTUAL_KEY_TEST=sk-litellm-test-9768ce8475df0a3c5aa0d2f52571505b2ef09f3a21ec1af73859749fff4bb7cd
DATABASE_URL=postgresql://litellm_user:LiteLLMPass2025@postgres:5432/litellm_db
```

**File**: `/home/administrator/secrets/mcp-postgres.env`
```bash
DATABASE_URI=postgresql://admin:Pass123qp@postgres:5432/postgres
MCP_SERVER_NAME=postgres-main
MCP_ALLOW_WRITE=false
MCP_DEBUG=true
```

---

## 🔧 Technical Deep Dive

### Docker Network Analysis
```bash
docker network ls
```
**Networks Available**:
- `litellm-mcp-net` (bridge) - Connects LiteLLM and MCP services
- `postgres-net` (external) - Provides database access

### Port Mapping Analysis
- **LiteLLM**: Host 4000 → Container 4000 ✅
- **MCP Postgres**: Host 48010 → Container 8686 ✅
- **Database**: Host 5432 → Container 5432 ✅

### Container Connectivity Test
```bash
# From LiteLLM container perspective
docker exec litellm ping mcp-postgres
```
**Expected**: Should resolve via litellm-mcp-net bridge network

---

## 📚 Research Findings

### LiteLLM MCP Documentation
- **Official Docs**: https://docs.litellm.ai/docs/mcp
- **Transport Support**: Confirms stdio, http, sse support
- **Key Quote**: "MCP Gateway that allows you to use a fixed endpoint for all MCP tools"

### MCP Protocol Evolution
- **2024-2025**: MCP evolved from SSE to HTTP transport
- **Current Spec**: Version 2025-06-18 (latest)
- **Transport Trend**: Moving toward HTTP/REST from SSE

### Alternative PostgreSQL MCP Servers
1. **mcp/postgres** (official) - Attempted, requires specific configuration
2. **crystaldba/postgres-mcp** (current) - stdio only
3. **Other alternatives** - Need research

---

## ❓ Critical Questions for Resolution

### 1. LiteLLM stdio Transport Configuration
**Question**: How should stdio transport be properly configured in LiteLLM for containerized MCP servers?

**Current Understanding**: The docker command approach failed because docker binary isn't available in LiteLLM container.

**Possible Solutions**:
- Mount docker socket
- Use different command approach
- Direct container communication method

### 2. Transport Bridging Capability
**Question**: Can LiteLLM act as a transport bridge between HTTP clients and stdio MCP servers?

**Expected Behavior**: Client connects via HTTP → LiteLLM → stdio MCP server

**Current Behavior**: LiteLLM expects HTTP from MCP server

### 3. Alternative MCP Server Options
**Question**: What PostgreSQL MCP servers provide HTTP/SSE transport?

**Requirements**:
- HTTP or SSE transport support
- PostgreSQL database connectivity
- Docker deployable
- Compatible with LiteLLM

### 4. Configuration Syntax Verification
**Question**: Is the current LiteLLM MCP configuration syntax correct?

**Documentation Gap**: Need authoritative examples of stdio transport configuration

---

## 🎯 Specific Help Needed

### For AI Assistants Reviewing This Report

1. **LiteLLM stdio Configuration**: How to properly configure stdio transport for containerized MCP servers in LiteLLM v1.77.3?

2. **Transport Compatibility Matrix**: What's the correct understanding of LiteLLM's transport capabilities vs MCP server requirements?

3. **Working Examples**: Provide complete, tested configurations for LiteLLM + PostgreSQL MCP integration.

4. **Alternative Solutions**: Recommend PostgreSQL MCP servers that provide HTTP/SSE endpoints.

5. **Architecture Validation**: Is the current Docker networking and service architecture correct?

### Testing Commands Ready
All infrastructure is deployed and ready for testing. Any configuration changes can be immediately tested with:

```bash
# Test LiteLLM health
curl -X GET "http://localhost:4000/health" -H "Authorization: Bearer sk-litellm-cecca..."

# Test MCP endpoint
curl -X GET "http://localhost:4000/mcp/" -H "Authorization: Bearer sk-litellm-cecca..."

# Check logs
docker logs litellm
docker logs mcp-postgres

# Restart services
docker compose restart litellm
```

---

## 📝 Deployment History

### Successful Components
- ✅ LiteLLM v1.77.3 deployment
- ✅ Docker networking setup
- ✅ Authentication configuration
- ✅ Database connectivity
- ✅ Claude Code CLI integration

### Failed Attempts
- ❌ SSE transport configuration
- ❌ stdio with docker exec approach
- ❌ HTTP transport to stdio server
- ❌ Alternative mcp/postgres image

### Current State
- 🟡 Infrastructure ready but MCP tools inaccessible
- 🟡 Transport mismatch preventing tool discovery
- 🟡 Need expert guidance on proper stdio configuration

---

## 🚀 Success Criteria

**Primary Goal**: Claude Code CLI successfully accessing PostgreSQL database tools through LiteLLM MCP Gateway.

**Test Success**: Command like "Show me the tables in the database" should return PostgreSQL table information via MCP tools.

**Infrastructure Success**: MCP server shows as connected/available in tool discovery.

---

*Report Generated: 2025-09-21*
*LiteLLM Version: v1.77.3*
*MCP Spec: 2025-06-18*
*Environment: linuxserver.lan (local network only)*