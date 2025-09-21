# Refined Plan: LiteLLM v1.77.3 MCP Gateway on linuxserver.lan

## 1. Context Snapshot
- Read and aligned with `/home/administrator/projects/AINotes/SYSTEM-OVERVIEW.md`, `network.md`, `security.md`, `logging.md`, `codingstandards.md`, `memoryrules.md`
- Current LiteLLM deployment attempts failed; infrastructure reset under `/home/administrator/projects/mcp/`
- Existing platform provides Postgres (`postgres-net`), Traefik with LAN DNS, centralized logging via Loki/Promtail, and Keycloak SSO
- Requirement: LAN-only access, LiteLLM `v1.77.3-stable`, no code changes to LiteLLM or MCP servers, MCPs may run in their own Docker containers

## 2. Goals and Guardrails
- Deliver a repeatable, declarative deployment for LiteLLM + MCP connectors
- Standardize how MCP transports (stdio, http, sse) are registered with LiteLLM
- Use existing infrastructure conventions (naming, secrets storage, networks, logging)
- Keep surface LAN-only; prepare hooks for later Traefik/OAuth fronting without requiring it now
- Provide validation and rollback guidance; highlight risks and open questions

## 3. Target Architecture Overview
- **Project name:** `mcp-gateway` (directories `/home/administrator/projects/mcp/gateway`, secrets in `/home/administrator/secrets/mcp-gateway.env`)
- **Core services (docker compose):**
  1. `mcp-litellm-proxy` – LiteLLM container pinned to `ghcr.io/berriai/litellm:v1.77.3-stable`
  2. `mcp-litellm-postgres` – (optional) dedicated Postgres 16-alpine if shared cluster is undesirable
  3. MCP connector containers (one per tool domain); start with `mcp-postgres` for DB access
- **Networks:**
  - Attach LiteLLM to `traefik-proxy` (future TLS/OAuth), `postgres-net` (for shared DB), and a new private network `mcp-gateway-net` for MCP connectors
  - Expose LiteLLM on host `4000/tcp` (LAN) and optionally register Traefik entry later
- **Storage:**
  - Mount configuration from `/home/administrator/projects/mcp/gateway/config/config.yaml`
  - Secrets exclusively in `/home/administrator/secrets/mcp-gateway.env` with `chmod 600`
  - Optional Postgres volume `mcp_gateway_pgdata`
- **Logging:**
  - Enable LiteLLM JSON logs → Promtail via Docker logging driver; ensure `labels` match observability conventions
  - MCP containers adopt same logging configuration to feed Promtail

## 4. MCP Transport Best Practices
| Transport | When to Use | Registration Pattern | Operational Notes |
|-----------|-------------|----------------------|-------------------|
| `sse` | Preferred for containerized MCPs on LAN | `mcp_servers.<alias>.url`, `transport: "sse"` | Use per-service container; expose fixed port; health check using `/status` if provided |
| `http` | For MCP servers exposing HTTP JSON endpoints | Same as SSE but `transport: "http"` | Ensure MCP implements MCP HTTP spec; configure auth headers via `auth_type`/`auth_value` |
| `stdio` | Lightweight local tools packaged with LiteLLM container | `transport: "stdio"`, `command`, `args`, `env` | Keep binaries inside LiteLLM image or bind-mount; avoid Docker exec hacks; for isolated tools wrap into SSE container instead |

**Auth & Headers:**
- Use `api_keys` list to map LiteLLM virtual keys allowed to see a server
- For per-request credentials, clients send `x-mcp-{alias}-{header}` (e.g., `x-mcp-db-authorization`)
- For static credentials, specify `auth_type: bearer_token` + `auth_value: ${MCP_POSTGRES_BEARER}` in config; inject values via environment

**Aliases & Scoping:**
- Keep `litellm_settings.mcp_aliases` small so clients can request only needed servers (`x-mcp-servers: db,fileops`)
- Document alias → service mapping in `gateway/README.md` (future)

## 5. Implementation Phases

### Phase A – Environment Preparation
1. Create project skeleton:
   ```bash
   mkdir -p /home/administrator/projects/mcp/gateway/config
   cp /home/administrator/projects/mcp/litellmprimer.md /home/administrator/projects/mcp/gateway/REFERENCES.md
   touch /home/administrator/projects/mcp/gateway/README.md
   ```
2. Create secrets file `/home/administrator/secrets/mcp-gateway.env` with:
   - `LITELLM_MASTER_KEY=` (new random value)
   - `DATABASE_URL=` pointing to either shared `postgres` container or dedicated service
   - `VIRTUAL_KEY_TEST=...` for mock clients
   - `MCP_POSTGRES_URL=postgresql://...` (no embedded secrets once Keycloak/OAuth used)
   - Additional MCP auth tokens (if required)
3. `chmod 600 /home/administrator/secrets/mcp-gateway.env`
4. If reusing central Postgres: create database + role (`litellm_db`, `litellm_user`) using admin credentials per `AINotes/integration.md`
5. Reserve host ports (LiteLLM 4000, MCP connectors e.g., 48010+) to avoid clashes; confirm with `sudo ss -tlnp` (approval needed if run)

### Phase B – Compose Definition
1. Draft `docker-compose.yml` under `gateway/` with services:
   - `litellm`: image pinned to `v1.77.3-stable`, command `litellm --config /app/config/config.yaml --detailed_debug`
   - Add explicit `user: "1000:1000"` if file permissions required
   - Mount config directory read-only
   - `env_file: /home/administrator/secrets/mcp-gateway.env`
   - Logging driver `json-file` with rotation (max-size 20m, max-file 5)
2. Define external networks:
   ```yaml
   networks:
     traefik-proxy:
       external: true
     postgres-net:
       external: true
     mcp-gateway-net:
       driver: bridge
   ```
3. If dedicated Postgres desired, include `postgres` service with `depends_on`, healthcheck, volume
4. Add baseline MCP connector (`mcp-postgres`) service:
   - Image `crystaldba/postgres-mcp:latest`
   - Environment `MCP_TRANSPORT=sse`, `MCP_PORT=8686`, `DATABASE_URI=${MCP_POSTGRES_URL}`
   - Expose host port `48010:8686` (LAN testing); join `mcp-gateway-net` and `postgres-net`
   - Healthcheck calling `curl -f http://localhost:8686/health || exit 1`
5. For each future MCP, replicate pattern with unique alias, container, env vars, and ports

### Phase C – LiteLLM Configuration (`config/config.yaml`)
- Structure:
  ```yaml
  litellm_settings:
    master_key: ${LITELLM_MASTER_KEY}
    database_url: ${DATABASE_URL}
    json_logs: true
    mcp_aliases:
      db: mcp_postgres
  general_settings:
    detailed_debug: true
  model_list:
    - model_name: gpt-4o-mock
      litellm_params:
        model: mock-response
        api_key: dummy
  virtual_keys:
    - api_key: ${VIRTUAL_KEY_TEST}
      models: ["gpt-4o-mock"]
      mcp_servers: ["db"]
  mcp_servers:
    mcp_postgres:
      transport: sse
      url: http://mcp-postgres:8686
      api_keys: [${VIRTUAL_KEY_TEST}]
      description: "PostgreSQL read tooling"
      health_check: /health
  ```
- Document difference between `virtual_keys[].mcp_servers` (limits exposure) vs header-based selection
- Add placeholders for future `stdio` or `http` entries (see Section 6)
- Include comments referencing `AINotes/codingstandards.md` for secret locations

### Phase D – Deployment & Verification
1. `docker compose pull` (ensures images cached before first run)
2. `docker compose up -d`
3. Verify container health:
   - `docker compose ps`
   - `docker compose logs litellm --tail 100`
4. Confirm LiteLLM API responding:
   ```bash
   curl -s http://linuxserver.lan:4000/v1/models \
     -H "Authorization: Bearer ${VIRTUAL_KEY_TEST}" | jq '.data[].tools'
   ```
   Expect tool metadata array for `db`
5. Validate MCP tool call via `/v1/responses` (preferred API for tool use):
   ```bash
   curl -s http://linuxserver.lan:4000/v1/responses \
     -H "Authorization: Bearer ${VIRTUAL_KEY_TEST}" \
     -H "Content-Type: application/json" \
     -H "x-mcp-servers: db" \
     -d '{
       "model": "gpt-4o-mock",
       "input": [{"role": "user", "content": [{"type": "text", "text": "List schemas"}]}]
     }' | jq
   ```
6. Expect `tool_calls` referencing MCP functions; confirm LiteLLM logs persist in Postgres (`litellm_logs` table)
7. Integrate with Open WebUI or Codex CLI by pointing to `http://linuxserver.lan:4000/v1` and including `x-mcp-servers` header

### Phase E – Observability, Backups, Hardening
- Enable Promtail scrape by adding labels `logging=enabled` and `com.docker.compose.project=mcp-gateway`
- Create Grafana dashboard using LiteLLM logs (request count, tool usage)
- Schedule nightly dump of LiteLLM Postgres schema using existing `/home/administrator/projects/postgres/backupdb.sh litellm_db`
- Optionally front LiteLLM with Traefik + OAuth2 proxy using Keycloak once LAN testing succeeds; follow pattern in `AINotes/security.md`
- Define maintenance runbook in `gateway/README.md` covering upgrades, scaling connectors, and log rotation

## 6. Protocol Recipes & Patterns

### 6.1 SSE MCP Container Template
```yaml
services:
  mcp-filesystem:
    image: ghcr.io/modelcontextprotocol/server-filesystem:latest
    environment:
      MCP_TRANSPORT: sse
      MCP_PORT: 8690
      MCP_ALLOWED_PATHS: /data/shared
    networks:
      - mcp-gateway-net
    ports:
      - "48020:8690"
```
- Register in LiteLLM:
  ```yaml
  mcp_servers:
    mcp_filesystem:
      transport: sse
      url: http://mcp-filesystem:8690
      allowed_hosts: ["*.linuxserver.lan"]
  ```

### 6.2 HTTP MCP Example
- Some MCP services expose pure HTTP endpoints (rare today). For those:
  ```yaml
  mcp_servers:
    mcp_monitoring:
      transport: http
      url: http://mcp-monitoring:8700
      auth_type: bearer_token
      auth_value: ${MCP_MONITORING_TOKEN}
  ```
- Ensure container presents `/health` endpoint for readiness; use Traefik middleware if later exposed externally

### 6.3 Stdio MCP (Local-only)
- Package binary inside LiteLLM container via `Dockerfile` overlay or bind mount a tools directory
- Example entry:
  ```yaml
  mcp_servers:
    mcp_toolshed:
      transport: stdio
      command: "/opt/mcp-toolshed/bin/start"
      args: ["--mode", "cli"]
      env:
        TOOLS_ROOT: /opt/mcp-toolshed
      allowed_paths:
        - /home/administrator/projects/shared
  ```
- Best practice: keep stdio usage minimal; if tool needs network or file access beyond LiteLLM container, wrap it in its own SSE server instead
- Add watchdog script to restart LiteLLM if stdio process exits unexpectedly

## 7. Expansion Roadmap
1. **Add more MCP connectors** (filesystem, fetch, n8n, timescaledb) following Section 6; document each in respective `/home/administrator/projects/mcp/<service>/CLAUDE.md`
2. **Promote from mock model** to real LLM endpoints once tool pipeline validated; update `model_list` with provider-specific keys stored in secrets file
3. **Traefik integration**: add labels for `litellm.linuxserver.lan` internal hostname, optional Keycloak-protected route for remote access
4. **High availability**: if demand grows, run LiteLLM replicas behind Traefik load balancer using shared Postgres + Redis for rate limits
5. **Security hardening**: enable IP allowlists on LiteLLM, rotate virtual keys, consider mutual TLS for MCP connectors if they move off-host
6. **Documentation**: update `/home/administrator/projects/AINotes/SYSTEM-OVERVIEW.md` and create `gateway/CLAUDE.md` after first successful deployment per coding standards

## 8. Risks and Open Questions
- **Version availability:** Confirm `ghcr.io/berriai/litellm:v1.77.3-stable` exists before deployment; fallback to latest `*-stable` if not published, document variance
- **Docker permissions:** Current CLI session lacks Docker socket access; ensure final deployment is executed by an administrator account with proper permissions
- **Database choice:** Decide between shared Postgres versus dedicated instance; shared reduces footprint but needs schema isolation and monitoring
- **Auth strategy for clients:** LAN-only now, but plan for API key rotation and potential Keycloak/OAuth layer when exposing beyond trusted hosts
- **MCP connector maturity:** Some community MCP servers may lack health endpoints or robust auth; vet each before production use

## Executive Summary
Use a new `mcp-gateway` project to deploy LiteLLM v1.77.3 via Docker Compose, anchored to existing LAN infrastructure and Postgres. Prefer SSE transport by running each MCP server in its own container, reserving HTTP for MCPs that natively expose it and stdio only for truly local tools bundled with LiteLLM. Configure LiteLLM with `mcp_servers` entries, scoped virtual keys, and JSON logging, then validate tool discovery and execution with `/v1/responses` calls. Once baseline is proven, expand connectors, integrate with observability and Traefik, and document everything per established AINotes standards.
