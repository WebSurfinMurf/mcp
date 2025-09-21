# Refined Plan: LiteLLM v1.77.3 MCP Gateway on linuxserver.lan

> **🚨 HARD RULE - LOCAL NETWORK DEPLOYMENT ONLY:**
> **This is a LOCAL NETWORK ONLY deployment using `linuxserver.lan`:**
> - **NEVER use Traefik** reverse proxy or routing
> - **NEVER use Keycloak** authentication or SSO
> - **NEVER use ai-servicers.com** DNS or HTTPS
> - **ALWAYS use direct port access** (e.g., `http://linuxserver.lan:4000`)
> - **ALWAYS use HTTP** (not HTTPS)
>
> **🔒 COMPLIANCE RULE:** These directives are HARD RULES and must NOT be violated unless:
> 1. Claude asks about a specific technical issue
> 2. User directly tells Claude to violate this order for that specific issue
>
> All references to Traefik/OIDC/authentication below are for FUTURE consideration only and must be IGNORED for this deployment.

## 0. Community-Supported MCP Gateway Options (Assignment Outcome)
| Candidate | Community Status | MCP Support | Fit for Requirement | Notes |
|-----------|------------------|-------------|---------------------|-------|
| **LiteLLM Proxy** (BerriAI) | 9.5k★ GitHub, active releases, Discord + docs | Native `mcp_servers` for `stdio`, `http`, `sse`; integrates auth, key mgmt, logging | ✅ Strong match; already part of stack; OpenAI-compatible API for clients (Claude Code, Gemini CLI, ChatGPT Codex, Open WebUI, VS Code) | Runs as central gateway; no code changes required; supports LAN-only deployments |
| **Model Context Runner** (Sourcegraph) | 2.5k★ GitHub, maintained; designed for Claude Desktop/VS Code | Focused on dev tooling; MCP registry but less customizable for multi-client sharing | ⚠️ Partial fit; better for per-user environments than central LAN service | Requires per-user runtimes; limited routing features |
| **mcp-proxy** (Community forks) | Multiple small repos (<200★) | Experimental HTTP/SSE forwarding | ❌ Weak fit; low adoption, unclear maintenance | Would require manual auth/logging layers |

**Recommendation:** Use **LiteLLM Proxy** as the central MCP gateway. It has the strongest community backing, already aligns with your infrastructure, and natively supports MCP transports plus the OpenAI-compatible API your clients expect. No code modifications to LiteLLM or third-party MCP servers are necessary—only configuration and Docker orchestration.

## 1. Context Snapshot
- Initialization files reviewed per `AINotes/memoryfiles.md` directive.
- Requirements confirmed in `projects/mcp/requirements.md`: LiteLLM lives under `projects/litellm`, individual MCP servers under `projects/mcp/{service}`.
- Infrastructure provides shared Postgres (`postgres-net`), Traefik reverse proxy, centralized observability, and LAN DNS (`*.linuxserver.lan`).
- Prior LiteLLM + MCP attempts failed; MCP directories reset for clean implementation.

## 2. Goals and Guardrails
- Keep deployment LAN-only while enabling future Traefik/OIDC layering.
- Pin LiteLLM to `v1.77.3-stable`, avoid modifying upstream code or MCP packages.
- Standardize registration patterns for `stdio`, `http`, and `sse` transports.
- Follow existing naming conventions and secrets handling (`/home/administrator/secrets/`).
- Provide validation, observability, and rollback guidance.

## 3. Target Architecture Overview
- **LiteLLM project root:** `/home/administrator/projects/litellm`
  - Config: `/home/administrator/projects/litellm/config/config.yaml`
  - Compose file: `/home/administrator/projects/litellm/docker-compose.yml`
  - Scripts/notes: `/home/administrator/projects/litellm/README.md` (update after success)
- **Secrets file:** `/home/administrator/secrets/litellm.env` (600 perms)
- **MCP services:** individual directories under `/home/administrator/projects/mcp/` (e.g., `/home/administrator/projects/mcp/postgres`, `/home/administrator/projects/mcp/filesystem`), each with its own Compose or Dockerfile as needed.
- **Networks:**
  - `traefik-proxy` (external, existing) for future reverse proxy integration.
  - `postgres-net` (external) for database connectivity.
  - `litellm-mcp-net` (new bridge) linking LiteLLM and MCP containers.
- **Core containers:**
  1. `litellm-proxy` (LiteLLM v1.77.3-stable)
  2. Optional `litellm-db` (Postgres 16-alpine) if not using shared cluster.
  3. `mcp-postgres` (community `crystaldba/postgres-mcp`) as first MCP connector.
  4. Additional MCP services (filesystem, fetch, n8n, etc.) deployed in their respective directories and attached to `litellm-mcp-net`.

## 4. MCP Transport Best Practices
| Transport | Usage Guidance | LiteLLM Config Snippet | Operational Notes |
|-----------|----------------|------------------------|-------------------|
| **SSE (preferred)** | Default for containerized MCP services on LAN. Run MCP in its own container, expose fixed port, connect via `litellm-mcp-net`. | ```yaml
mcp_servers:
  db_main:
    transport: sse
    url: http://mcp-postgres:8686
    api_keys: [${LITELLM_VIRTUAL_KEY_TEST}]
``` | Supports long-lived connections, streaming, simple firewalling. Provide health endpoints where available. |
| **HTTP** | Use if MCP server exposes RESTful MCP interface (rare today). | ```yaml
mcp_servers:
  monitoring:
    transport: http
    url: http://mcp-monitor:8700
    auth_type: bearer_token
    auth_value: ${MCP_MONITOR_TOKEN}
``` | Ensure server adheres to MCP HTTP spec; configure auth headers through LiteLLM. |
| **Stdio** | Only for lightweight local tools packaged alongside LiteLLM in `/home/administrator/projects/litellm/tools`. | ```yaml
mcp_servers:
  local_tools:
    transport: stdio
    command: "/app/tools/run"
    args: ["--mode", "cli"]
    env:
      TOOLS_ROOT: /app/tools
``` | Avoid wrapping Docker containers with stdio; instead expose them via SSE. Requires binaries accessible within LiteLLM container image or bind-mount. |

**Auth & Header Tips:**
- Use `api_keys` to scope LiteLLM virtual keys to specific MCP servers.
- Clients select servers via `x-mcp-servers` header (`db_main,fs_local`).
- Per-request headers forwarded via `x-mcp-{alias}-{header}` (e.g., `x-mcp-db_main-authorization`).
- Static secrets can be injected with `auth_type: bearer_token` and `auth_value` placeholder variables that resolve from `litellm.env`.

## 5. Implementation Phases

### Phase A – Environment Preparation
1. Ensure project structure:
   ```bash
   cd /home/administrator/projects/litellm
   mkdir -p config tools tmp
   ```
2. Create secrets file `/home/administrator/secrets/litellm.env` containing (replace placeholders):
   ```bash
   LITELLM_MASTER_KEY=sk-...
   DATABASE_URL=postgresql://litellm_user:...@postgres:5432/litellm_db
   LITELLM_VIRTUAL_KEY_TEST=litellm-test-key-...
   ```
   Set permissions `chmod 600 /home/administrator/secrets/litellm.env`.
3. **Database strategy decision:**
   - **Option A (recommended):** Reuse existing Postgres on `postgres-net`; keep `DATABASE_URL` pointed at that hostname.
   - **Option B:** Deploy the optional `litellm-db` service below; update `DATABASE_URL` to reference it.
   Choose one approach before continuing.
4. If using shared Postgres:
   - Follow `AINotes/integration.md` to create `litellm_db` and `litellm_user`.
   - Grant read privileges for MCP connectors as needed; keep write access disabled until explicitly required.
5. Reserve LAN ports (LiteLLM `4000`, MCP connectors `48xxx`) ensuring no collisions (`sudo ss -tlnp` if permissible).
6. Populate `/home/administrator/projects/mcp/postgres/` with connector assets (compose file, docs) for the community `crystaldba/postgres-mcp` image.

### Phase B – LiteLLM Docker Compose (`/home/administrator/projects/litellm/docker-compose.yml`)
```yaml
version: "3.9"

services:
  litellm-proxy:
    image: ghcr.io/berriai/litellm:v1.77.3-stable
    container_name: litellm-proxy
    restart: unless-stopped
    command: ["--config", "/app/config/config.yaml", "--detailed_debug"]
    env_file: /home/administrator/secrets/litellm.env
    volumes:
      - ./config:/app/config:ro
    ports:
      - "4000:4000"
    networks:
      - traefik-proxy
      - postgres-net
      - litellm-mcp-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    logging:
      driver: json-file
      options:
        max-size: "20m"
        max-file: "5"

  # Optional dedicated Postgres for LiteLLM metadata
  litellm-db:
    image: postgres:16-alpine
    container_name: litellm-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${LITELLM_DB_USER}
      POSTGRES_PASSWORD: ${LITELLM_DB_PASSWORD}
      POSTGRES_DB: litellm_db
    volumes:
      - litellm_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${LITELLM_DB_USER} -d litellm_db"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - litellm-mcp-net
```
Add external network declarations and optional volume:
```yaml
networks:
  traefik-proxy:
    external: true
  postgres-net:
    external: true
  litellm-mcp-net:
    driver: bridge

volumes:
  litellm_pgdata:
```
If relying on shared Postgres, omit `litellm-db` service and ensure `DATABASE_URL` points to existing server on `postgres-net`.

### Phase C – LiteLLM Configuration (`config/config.yaml`)
```yaml
litellm_settings:
  master_key: ${LITELLM_MASTER_KEY}
  database_url: ${DATABASE_URL}
  json_logs: true
  mcp_aliases:
    db: db_main

general_settings:
  detailed_debug: true

model_list:
  - model_name: gpt-4o-mock
    litellm_params:
      model: mock-response
      api_key: mock

virtual_keys:
  - api_key: ${LITELLM_VIRTUAL_KEY_TEST}
    models: ["gpt-4o-mock"]
    mcp_servers: ["db"]

mcp_servers:
  db_main:
    transport: sse
    url: http://mcp-postgres:8686
    api_keys: [${LITELLM_VIRTUAL_KEY_TEST}]
    description: "PostgreSQL metadata + health tooling"
    health_check: /health
```
Add stubs for future HTTP/stdio services with comments referencing Section 4 patterns.

### Phase D – MCP Connector Deployment (Example: Postgres)
1. In `/home/administrator/projects/mcp/postgres/docker-compose.yml`:
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
         MCP_TRANSPORT: sse
         MCP_PORT: 8686
         MCP_ALLOW_WRITE: "false"
       ports:
         - "48010:8686"
       networks:
         - litellm-mcp-net
         - postgres-net
       healthcheck:
         test: ["CMD-SHELL", "curl -fsS http://localhost:8686/health || exit 1"]
         interval: 15s
         timeout: 5s
         retries: 5
         start_period: 20s

   networks:
     litellm-mcp-net:
       external: true
     postgres-net:
       external: true
   ```
2. Create `/home/administrator/secrets/mcp-postgres.env` containing `DATABASE_URI=postgresql://...` (read-only credentials preferred) and set permissions `chmod 600 /home/administrator/secrets/mcp-postgres.env`.
3. Document service details in `/home/administrator/projects/mcp/postgres/CLAUDE.md` once operational.

### Phase E – Deployment & Verification
0. **Create shared network:** `docker network create litellm-mcp-net` (safe to rerun; Docker will warn if it already exists).
1. Pull images: `docker compose pull` within both `projects/litellm` and each MCP directory.
2. Start MCP connectors first (e.g., `docker compose up -d` inside `projects/mcp/postgres`).
3. Start LiteLLM: `docker compose up -d` inside `projects/litellm`.
4. Validate container health:
   ```bash
   docker compose ps
   docker compose logs litellm-proxy --tail 100
   ```
5. Confirm tool discovery:
   ```bash
   curl -s http://linuxserver.lan:4000/v1/models \
     -H "Authorization: Bearer ${LITELLM_VIRTUAL_KEY_TEST}" | jq '.data[] | select(.id=="gpt-4o-mock").tools'
   ```
6. Verify MCP server registration explicitly:
   ```bash
   curl -s http://linuxserver.lan:4000/v1/models \
     -H "Authorization: Bearer ${LITELLM_VIRTUAL_KEY_TEST}" \
     -H "x-mcp-servers: db" | jq '.data[] | select(.id=="gpt-4o-mock").mcp_servers'
   ```
7. Test MCP call via `/v1/responses` (preferred for tool execution):
   ```bash
   curl -s http://linuxserver.lan:4000/v1/responses \
     -H "Authorization: Bearer ${LITELLM_VIRTUAL_KEY_TEST}" \
     -H "Content-Type: application/json" \
     -H "x-mcp-servers: db" \
     -d '{
       "model": "gpt-4o-mock",
       "input": [{"role": "user", "content": [{"type": "text", "text": "List schemas."}]}]
     }' | jq
   ```
8. Verify LiteLLM persisted log entry in Postgres (`SELECT model, user_id, request_tags->'tool_calls' FROM litellm_logs ORDER BY start_time DESC LIMIT 5;`).

### Phase F – Client Integration
- **Claude Code CLI / Gemini CLI / ChatGPT Codex CLI:** Point `api_base` to `http://linuxserver.lan:4000/v1`, include `Authorization: Bearer <virtual key>` and `x-mcp-servers` header.
- **Open WebUI:** Configure OpenAI-compatible backend using LiteLLM endpoint; ensure environment allows custom headers for MCP usage.
- **VS Code (MCP extension):** Add LiteLLM entry in `mcp.json` referencing LAN URL and key.
- Document connection instructions in `/home/administrator/projects/litellm/README.md`.

### Phase G – Observability, Backups, Hardening
- Promtail auto-discovers containers; ensure labels `logging=enabled` and `project=litellm`.
- Add Grafana dashboard for LiteLLM metrics (request count, latency, tool usage) using Loki queries.
- Backup LiteLLM Postgres schema nightly with existing scripts (`/home/administrator/projects/postgres/backupdb.sh litellm_db`).
- Plan future Traefik/OAuth2 proxy integration (Keycloak) once LAN-only testing is complete.
- Rotate virtual keys periodically; document rotation procedure in `litellm/README.md`.

## 6. Protocol Recipes & Patterns
- **SSE Template:** Provided in Phase D.
- **HTTP Template:** See Section 4 examples; ensure MCP server exposes `/health`.
- **Stdio Template:** Package tool binaries within `/home/administrator/projects/litellm/tools`; update Docker image via overlay or bind mount. Keep usage minimal; prefer SSE wrappers for better isolation.

## 7. Expansion Roadmap
1. Deploy additional MCP services (`filesystem`, `fetch`, `n8n`, `timescaledb`). Each gets its own directory, Compose file, secrets, and LiteLLM `mcp_servers` entry.
2. Replace mock model with real providers once tool pipeline validated; add provider API keys to `litellm.env` and extend `model_list`.
3. Add Traefik labels to LiteLLM container for `litellm.linuxserver.lan` hostname and optional OAuth2 proxy for authenticated external access.
4. Evaluate LiteLLM rate limiting, quotas, and Redis caching if usage increases.
5. Update AINotes docs (`SYSTEM-OVERVIEW.md`, `network.md`, `security.md`) post-deployment per coding standards.

## 8. Risks and Open Questions
- **Image availability:** Verify `ghcr.io/berriai/litellm:v1.77.3-stable` exists; fall back to latest `*-stable` if necessary and capture variance in docs.
- **Permission boundaries:** Current CLI lacks Docker socket access; final deployment must be run with appropriate privileges.
- **Database sharing vs isolation:** Decide whether LiteLLM uses shared cluster or dedicated container; document rationale.
- **Client header support:** Ensure each client (e.g., Open WebUI) can send `x-mcp-servers`; may require middleware updates.
- **MCP connector maturity:** Some community MCP containers may lack full health endpoints or fine-grained auth—evaluate before production adoption.

## Executive Summary
Community analysis identifies the LiteLLM Proxy as the most robust, widely supported MCP gateway for your LAN environment. Deploy LiteLLM v1.77.3-stable from `/home/administrator/projects/litellm`, attach it to per-service MCP containers located under `/home/administrator/projects/mcp/{service}`, and standardize on SSE transport while documenting HTTP/stdio fallbacks. Configure LiteLLM’s `mcp_servers` with scoped virtual keys, validate functionality using `/v1/responses`, and integrate with local clients (Claude Code, Gemini CLI, ChatGPT Codex CLI, Open WebUI, VS Code). Once the baseline works, expand connectors, fold LiteLLM into observability/backup routines, and prepare Traefik + Keycloak hardening for broader network use.
