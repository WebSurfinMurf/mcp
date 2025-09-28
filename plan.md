# MCP Service Enablement Plan (Direct stdio + SSE, No Proxy)

## Objectives
- Keep every existing `mcp-bridge.py` stdio adapter fully operational so Codex CLI remains on the current transport during the transition.
- Enable native SSE transport **only** for services already deployed via Docker containers (`mcp-filesystem`, `mcp-minio`, `mcp-n8n`, `mcp-playwright`, `mcp-timescaledb`).
- Register each SSE-capable service with Claude CLI using host-accessible URLs (localhost bindings) and obtain administrator validation before touching the next service.
- Explicitly **avoid** any MCP proxy layer or use of the legacy `mcp/proxy/` assets.
- Document SSE availability while acknowledging that browser clients (Open-WebUI) can only reach services whose containers expose real SSE handlers.

## Requirements & Constraints
- Do **not** remove or refactor the stdio bridges; every redeploy must be followed by a quick stdio smoke test to prove Codex remains functional.
- Touch only `/home/administrator/projects/mcp/<service>` directories that already have Docker-based FastAPI servers.
- FastAPI servers must expose:
  - `GET /health` – service status
  - `GET /sse` – real SSE request/response loop (pattern copied from `mcp-filesystem`)
  - `POST /mcp` – HTTP fallback (already present)
- Containers publish host ports on `127.0.0.1:<PORT>`; Claude CLI must therefore use `http://localhost:<PORT>/sse` for registration. Docker DNS names such as `mcp-filesystem` are **not** accessible from the host.
- Confirm actual endpoint paths before registration; do **not** assume `/mcp/sse`.
- Record changes in the corresponding `CLAUDE.md` and `AINotes/MCP-STATUS-REPORT.md` **only after** the administrator validates a phase.
- Each phase ends with an explicit “pause for admin validation” checkpoint.
- Browser-based clients (Open-WebUI) cannot trigger stdio bridges; they can only use the SSE endpoints once implemented.

## Phase 0 – Environment & Baseline Checks
1. Verify Claude CLI readiness:
   - `claude --version`
   - `claude mcp list`
   - Confirm `~/.config/claude/mcp-settings.json` exists.
2. Capture current registrations for reference.
3. Run baseline tests to prove existing services still respond:
   - `claude --no-web -c "Use fetch to check status"` (if registered)
   - `python3 mcp/filesystem/mcp-bridge.py` smoke command (stdio)
4. Note current Open-WebUI limitation: only services with working SSE endpoints will be reachable from the browser.
5. Proceed to Phase 1 only after environment confirmation.

## Execution Strategy (Post-Phase 0)
1. Process services sequentially: `filesystem` → `minio` → `n8n` → `playwright` → `timescaledb`.
2. For each service:
   - Implement or confirm filesystem-style SSE handling.
   - Redeploy container and verify both SSE and stdio paths.
   - Register with Claude CLI using localhost URLs.
   - Run a predictable test matrix (SSE + stdio + health).
   - Pause for administrator validation before moving forward.
3. Keep the legacy proxy artifacts untouched and document that they remain out of scope.

## Phase 1 – `mcp-filesystem` (Baseline Template)
1. **Audit Current State**
   - Confirm `mcp/filesystem/src/server.py` already implements the queue-based SSE handler.
   - Verify `docker-compose.yml` binds `127.0.0.1:9073:8000` and container name `mcp-filesystem`.
   - Run stdio smoke test: `echo '{"jsonrpc": "2.0", "method": "initialize", "id": 1}' | python3 mcp/filesystem/mcp-bridge.py`.
2. **Redeploy & Health Check**
   - `cd mcp/filesystem && ./deploy.sh`
   - Health: `curl -s http://localhost:9073/health`
   - SSE handshake: `curl -i -H "Accept: text/event-stream" http://localhost:9073/sse` (expect 200 + event-stream headers).
3. **Claude Registration**
   - `claude mcp remove filesystem --scope user || true`
   - `claude mcp add filesystem http://localhost:9073/sse --transport sse --scope user`
   - Confirm with `claude mcp list`.
4. **Test Matrix**
   - SSE: `claude --no-web -c "Use filesystem to list the contents of the /workspace directory"`
   - stdio (post-deploy sanity): rerun the bridge command to ensure Codex path still works.
5. **Admin Validation Checkpoint**
   - Present outputs, await explicit admin approval before touching other services.
6. **Documentation (Post-Approval)**
   - Update `mcp/filesystem/CLAUDE.md` with working SSE details, localhost registration command, and test commands.
   - Append status entry to `AINotes/MCP-STATUS-REPORT.md` noting SSE readiness and stdio parity.

## Phases 2–5 – Remaining Containers (`minio`, `n8n`, `playwright`, `timescaledb`)
For each service, execute the following only after the previous phase receives admin sign-off:

1. **Gap Analysis**
   - Review `mcp/<service>/src/server.py` to identify missing SSE logic.
   - Confirm port binding in `docker-compose.yml` (e.g., minio `127.0.0.1:9076:8000`, n8n `9074`, playwright `9075`, timescaledb `48011`).
   - Validate stdio bridge via `python3 mcp/<service>/mcp-bridge.py` smoke command.
2. **Implement SSE Handling**
   - Inject the filesystem-style `asyncio.Queue` reader and dispatcher into `/sse`.
   - Ensure heartbeat/ping events remain for idle periods.
   - Run unit/lint checks if available.
3. **Redeploy & Validate**
   - `cd mcp/<service> && ./deploy.sh`
   - Health: `curl -s http://localhost:<port>/health`
   - SSE: `curl -i -H "Accept: text/event-stream" http://localhost:<port>/sse`
   - stdio: post-deploy bridge smoke test.
4. **Claude Registration**
   - `claude mcp remove <service> --scope user || true`
   - `claude mcp add <service> http://localhost:<port>/sse --transport sse --scope user`
   - `claude mcp list`
5. **Test Matrix**
   - SSE example (per service):
     - MinIO: `claude --no-web -c "Use minio to list all buckets"`
     - n8n: `claude --no-web -c "Use n8n to list workflows"`
     - Playwright: `claude --no-web -c "Use playwright to take a screenshot of https://example.com"`
     - TimescaleDB: `claude --no-web -c "Use timescaledb to list databases"`
   - stdio: run the bridge command with an `initialize` payload.
6. **Admin Validation Checkpoint**
   - Share results, wait for explicit go-ahead before proceeding to the next service.
7. **Documentation (Post-Approval)**
   - Update service `CLAUDE.md` with SSE registration/test details.
   - Record status in `AINotes/MCP-STATUS-REPORT.md`, including Open-WebUI accessibility note (only once SSE confirmed).

## Admin Interaction Points
- After Phase 0 – confirm environment readiness.
- After Phase 1 – approve filesystem results before touching minio.
- After each subsequent phase – approve before moving to the next service.

## Finalization
- Once all five services complete the cycle, prepare a consolidated report summarizing:
  - SSE endpoints (localhost URLs)
  - stdio + SSE validation commands
  - Open-WebUI compatibility status (identify services now accessible via SSE)
  - Any outstanding issues or follow-up work
- Retain stdio bridges as supported fallbacks until the administrator decides they can be deprecated.

_Last updated: 2025-09-28 (Codex)_
