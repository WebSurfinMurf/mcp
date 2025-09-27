# 📋 Project Overview
Central MCP proxy that aggregates multiple MCP services behind a single Server-Sent Events gateway using TBXark/mcp-proxy. Runs entirely on the local LAN (`linuxserver.lan`) without Traefik or Keycloak.

## 🟢 Current State (2025-09-25)
- **Status**: ✅ Central proxy reachable on the LAN and serving registered MCP services
- **Proxy Image**: `ghcr.io/tbxark/mcp-proxy:v0.39.1`
- **Listen Address**: `http://linuxserver.lan:9090`
- **Authentication**: Bearer token loaded from `/home/administrator/secrets/mcp-proxy.env`
- **Backends wired**: PostgreSQL (crystaldba/postgres-mcp) and Fetch bridge; filesystem/timescaledb ready but not registered by default

## 📝 Recent Work & Changes
- Added pinned Docker Compose stack and config templating for the central proxy.
- Replaced legacy LiteLLM MCP compose with dedicated SSE services for Postgres and TimescaleDB.
- Scaffolded filesystem and fetch stdio→SSE bridge containers with reusable scripts.
- Created secrets file placeholders and `render-config.sh` helper for injecting the auth token.

## 🏗️ Architecture
```
Clients (Claude Code, VS Code, Open WebUI)
        │  SSE
        ▼
Central Proxy (linuxserver.lan:9090)
        ├── postgres → crystaldba/postgres-mcp @ 8686 (mcp-net + postgres-net)
        ├── timescaledb → crystaldba/postgres-mcp @ 8687 (mcp-net + postgres-net)
        ├── filesystem → mcp-filesystem-bridge @ 9071 (stdio bridge)
        └── fetch → mcp-fetch-bridge @ 9072 (stdio bridge)
```
- Network: all containers attach to the external `mcp-net`. Database services also join `postgres-net` for database connectivity.
- Auth: Central proxy enforces bearer token. Bridges currently rely on network isolation (add `--with-auth` if exposure required).

## ⚙️ Configuration
- **Compose file**: `mcp/proxy/docker-compose.yml`
- **Config template**: `mcp/proxy/config/config.template.json`
- **Token injection script**: `mcp/proxy/render-config.sh`
- **Secrets**:
  - `/home/administrator/secrets/mcp-proxy.env`
  - `/home/administrator/secrets/mcp-postgres.env`
  - `/home/administrator/secrets/mcp-timescaledb.env`
- Generated config (`config/config.json`) is git-ignored; render it before starting the proxy.

## 🌐 Access & Management
- Proxy base URL: `http://linuxserver.lan:9090/`
- Active SSE routes:
  - `http://linuxserver.lan:9090/postgres/sse`
  - `http://linuxserver.lan:9090/fetch/sse`
- Optional (register via `add-to-central.sh`):
  - `http://linuxserver.lan:9090/timescaledb/sse`
  - `http://linuxserver.lan:9090/filesystem/sse`
- Clients must send header `Authorization: Bearer <token from mcp-proxy.env>`.

## 🔗 Integration Points
- **Postgres MCP** (`mcp/postgres/docker-compose.yml`): connects to main PostgreSQL via `postgres-net`.
- **TimescaleDB MCP** (`mcp/timescaledb/docker-compose.yml`): connects to TimescaleDB container on `postgres-net`.
- **Filesystem bridge** (`mcp/filesystem/bridge`): exposes `@modelcontextprotocol/server-filesystem` over SSE with workspace mounted read-only.
- **Fetch bridge** (`mcp/fetch/bridge`): exposes `mcp-server-fetch` over SSE.

## 🛠️ Operations
1. **Manage proxy token**
   ```bash
   # Create/update the env file without committing the value
   install -m 600 /dev/null /home/administrator/secrets/mcp-proxy.env
   echo "MCP_PROXY_TOKEN=$(openssl rand -hex 32)" > /home/administrator/secrets/mcp-proxy.env
   ```
2. **Render proxy config (keeps existing services)**
   ```bash
   cd /home/administrator/projects/mcp/proxy
   ./render-config.sh
   ```
3. **Start services**
   ```bash
   # Central proxy
   docker compose up -d

   # Database SSE services
   (cd ../postgres && docker compose up -d)
   (cd ../timescaledb && docker compose up -d)

   # Bridges (build locally)
   (cd ../filesystem/bridge && docker compose up -d --build)
   (cd ../fetch/bridge && docker compose up -d --build)
   ```
4. **Register additional services**
   ```bash
   cd /home/administrator/projects/mcp
   ./add-to-central.sh --service filesystem --port 9071 --add-auth --test --test-token "$MCP_PROXY_TOKEN"
   ```
   *(Repeat for other services as needed.)*
5. **Smoke test**
   ```bash
   export MCP_PROXY_TOKEN=$(grep MCP_PROXY_TOKEN /home/administrator/secrets/mcp-proxy.env | cut -d= -f2)
   curl -f http://linuxserver.lan:9090/
   curl -N -H 'Accept: text/event-stream' -H "Authorization: Bearer $MCP_PROXY_TOKEN" \
     http://linuxserver.lan:9090/postgres/sse | head
   ```
6. **Sync Claude CLI configuration**
   ```bash
   cd /home/administrator/projects/mcp/proxy
   ./sync-claude-config.sh
   ```
   *Creates `~/.config/claude/mcp-settings.json` pointing at `linuxserver.lan` with the current token.*

## 🔧 Troubleshooting
- **Proxy returns 401**: ensure `config/config.json` was rendered after updating token.
- **SSE connection hangs**: confirm backend container is healthy and reachable via `mcp-net`.
- **Bridge build fails**: host must have Docker network `mcp-net` created (`docker network create mcp-net`).
- **Database auth errors**: verify credentials inside respective `secrets/mcp-*.env` files match live databases.
- **Healthcheck failures**: upstream images may lack `wget`; replace with `CMD-SHELL`, e.g. `test: ["CMD-SHELL", "</dev/tcp/localhost/9090"]`.

## 🔐 Security Notes
- Keep `/home/administrator/secrets/mcp-proxy.env` permissioned to `600`.
- Bridges expose stdio tools only on `mcp-net`. Do not publish ports unless debugging.
- Rotate `MCP_PROXY_TOKEN` regularly; rerun `render-config.sh` and restart proxy afterward.

## 🔄 Related Services
- `/home/administrator/projects/mcp/add-bridge.sh` – scaffold new stdio bridges.
- `/home/administrator/projects/mcp/add-to-central.sh` – manage proxy registrations.
- `/home/administrator/projects/mcp/list-central.sh` – inspect active services.
