# MCP HTTP Migration Plan (TBXark Proxy via Docker Compose)

> **Directive:** Follow the community download setup for TBXark/mcp-proxy exactly as documented (official Docker image + docker-compose). Do not modify the TBXark container image. Preserve existing stdio bridges while introducing a Docker Compose–managed proxy that exposes the filesystem service over Streamable HTTP on port 9090. If any MCP service cannot conform to this recommended pattern, escalate before proceeding.

## Scope & Goals
- Keep current stdio access untouched so Codex (stdio) continues to work.
- Stand up the community-supported TBXark MCP proxy bound to `http://localhost:9090` under `/home/administrator/projects/mcp/proxy`, using the official `ghcr.io/tbxark/mcp-proxy:latest` image and docker-compose workflow.
- Register only the filesystem MCP (stdio) server with the proxy for the initial validation cycle.
- Once filesystem Streamable HTTP works with Claude, document results and prepare for subsequent services (minio, n8n, playwright, timescaledb, postgres). For each future service, confirm it fits the recommended configuration; if not, pause and report back.

## Architecture Snapshot (Phase 0)
```
Claude / Open WebUI / VSCode MCP
            ↓
   TBXark MCP Proxy (:9090)
            ↓
     stdio subprocess (filesystem)
```
- Proxy listens on host port 9090.
- Filesystem service launches via `npx @modelcontextprotocol/server-filesystem` inside the proxy container.
- Future services will be added only after filesystem passes Claude validation and compliance with the community setup is confirmed.

## Phase 0 – Filesystem over Streamable HTTP

### 1. Prepare Proxy Workspace
```bash
mkdir -p /home/administrator/projects/mcp/proxy
cd /home/administrator/projects/mcp/proxy
```

### 2. Author `docker-compose.yml`
```yaml
version: "3.8"

services:
  mcp-proxy:
    image: ghcr.io/tbxark/mcp-proxy:latest
    container_name: mcp-proxy
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./config.json:/config.json
      - /home/administrator/projects:/workspace:ro
    networks:
      - mcp-net
    command: ["-config", "/config.json"]
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:9090/health"]
      interval: 30s
      timeout: 5s
      retries: 3

networks:
  mcp-net:
    external: true
```
- This matches the community download workflow: official container + mounted config via compose.

### 3. Author `config.json` (Filesystem Only)
```json
{
  "mcpProxy": {
    "addr": ":9090",
    "baseURL": "http://localhost:9090",
    "name": "Local MCP Proxy",
    "type": "streamable-http",
    "options": {
      "logEnabled": true,
      "panicIfInvalid": false
    }
  },
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem@0.2.3", "/workspace"],
      "env": {
        "NODE_NO_WARNINGS": "1"
      }
    }
  }
}
```
- No deviations from the recommended configuration. Streamable HTTP is enabled by setting the proxy `type` to `streamable-http`; individual stdio services omit a `type` field (the proxy infers stdio from the `command`). If filesystem requirements ever conflict with this pattern, pause and report.

### 4. Create Shared Docker Network (host task)
```bash
docker network create mcp-net
```
- Network scope matches the community guidance for connecting additional MCP containers.

### 5. Launch Proxy (host task)
```bash
cd /home/administrator/projects/mcp/proxy
docker compose up -d
```
- Verify container: `docker ps --filter name=mcp-proxy`.
- Do **not** edit or rebuild the TBXark image; only use the official download.

### 6. Validate Filesystem Streamable HTTP
```bash
curl -sS -X POST http://localhost:9090/filesystem/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{}}}'
```
- Expect HTTP 200/202 with JSON-RPC body and an `Mcp-Session-Id` header.
- Follow with `tools/list` using returned session id:
```bash
curl -sS -X POST http://localhost:9090/filesystem/mcp \
  -H 'Content-Type: application/json' \
  -H "Mcp-Session-Id: <session-id>" \
  -d '{"jsonrpc":"2.0","id":"2","method":"tools/list","params":{}}'
```
- Confirm response enumerates filesystem tools.

### 7. Claude Registration & Smoke Test
1. Update Claude CLI to register `filesystem` with Streamable HTTP URL `http://localhost:9090/filesystem/mcp`.
2. Run `phase1-claude.sh` once updated to target proxy endpoint (requires host execution).
3. Capture logs via `docker logs mcp-proxy` and `docker logs mcp-filesystem` if issues arise.

### 8. Documentation & Status Updates
- Record validation steps and outputs in `mcp/filesystem/CLAUDE.md` and `AINotes/MCP-STATUS-REPORT.md`.
- Update `mcp/planhttp.status.md` items as tasks complete.
- Note any deviations or required configuration tweaks for future services; escalate if they require nonstandard proxy changes.

## Phase 1+ – Future Services (Placeholder)
- Once filesystem passes in Claude, extend `config.json` with additional MCP containers one at a time (minio → n8n → playwright → timescaledb → postgres).
- For each service, adhere to the community download setup (official image + docker-compose). If a service cannot be expressed within this pattern, stop, document the blocker, and request guidance.
- After each addition repeat validation, update documentation, and register with Claude individually.
- Enable auth tokens + TLS before exposing beyond localhost.

---
*This plan enforces the official community deployment path for TBXark/mcp-proxy. No container customization is permitted; docker-compose orchestration and standard configuration files must be used throughout. Escalate any service that requires deviations.*
