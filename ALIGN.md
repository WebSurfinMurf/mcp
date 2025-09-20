# LiteLLM MCP Alignment Plan

## Current State (2025-09-18)
- LiteLLM 1.77.1 exposes LAN (`http://litellm.linuxserver.lan`) and external (`https://litellm.ai-servicers.com`) entrypoints.
- `projects/litellm/config.yaml` registers `mcp_postgres` and `mcp_filesystem` via stdio; monitoring slot reserved.
- Secrets (`secrets/litellm.env`) include master key, Postgres URL, and filesystem allowlist.
- LAN `/mcp/tools` curl test succeeds when run on LinuxServer; log `lan-mcp-tools-2025-09-18-075003.log` captures SSE heartbeat pings.
- Codex CLI config points to LiteLLM but no end-to-end tool invocation has been captured yet.
- Open WebUI MCP probe still fails because LiteLLM only relays tool catalogs.
- VS Code / MCP documentation now includes example config + Windows credential guidance (added this session).

## Target Outcomes (from `CODEXMCP.md`)
1. Dual-host Traefik routing fully validated and documented in service runbooks.
2. LAN `/mcp/tools` calls return complete tool catalogs (SSE) with proper headers.
3. Client matrix (Codex CLI, Open WebUI, VS Code) configured and tested against LAN host.
4. Validation artifacts stored; documentation refreshed across LiteLLM + client projects.
5. Outstanding questions resolved (firewall path, scoped keys, future MCP services).

## Gap Analysis
- **Routing validation**: LAN route works ad-hoc but lacks Traefik label verification and permanent documentation.
- **Tool catalog verification**: Need scripted check capturing SSE events, not just keep-alive pings.
- **Codex CLI**: Awaiting `codex mcp` execution proof + doc updates.
- **Open WebUI**: Needs clarified expectations, header configuration, and failure documentation update.
- **VS Code**: Missing example `mcp_servers.json` and Windows credential instructions in version-controlled docs.
- **Artifacts & Docs**: No recorded outputs in `projects/litellm/evaluation/`; `MCP-INTEGRATION-STATUS.md` not updated.
- **Operational notes**: Firewall allowances and scoped key decision still open.

## Remediation Plan

### Phase 1 – Network & Gateway Verification
1. Inspect Traefik labels in `projects/litellm/docker-compose.yml`; confirm both hosts map to LiteLLM service. ✅ Completed 2025-09-18.
2. Run scripted curl (SSE) test capturing tool catalog events; store log under `projects/litellm/evaluation/lan-mcp-tools-<date>.log`. ✅ Completed 2025-09-18 on LinuxServer using `test-lan-mcp-tools.sh`; log saved as `lan-mcp-tools-2025-09-18-075003.log` (contains keep-alive pings).
3. Update `projects/litellm/CLAUDE.md` (or equivalent runbook) with LAN routing requirements and curl command. ✅ Added 2025-09-18 including troubleshooting notes.

### Phase 2 – MCP Server & Secrets Audit
1. Reconfirm `mcp_servers` definitions and environment variables match CODEXMCP expectations (no local modifications).
2. Document secret sources (`secrets/mcp-postgres.env`, `secrets/litellm.env`) and restart procedure in runbooks.

### Phase 3 – Client Matrix Validation
1. **Codex CLI**
   - Ensure config includes persistent `x-mcp-servers` header. ✅ Verified in `~/.codex/config.toml` (2025-09-18).
   - Run `codex mcp list` + sample invocation; save transcript under `projects/litellm/evaluation/`. ⚠️ `codex mcp list` succeeds; tool invocation requires interactive workflow not available for automated testing (see evaluation log).
   - Update CLI onboarding doc with results. ✅ Notes added to `projects/litellm/CLAUDE.md`.
2. **Open WebUI**
   - Verify environment variables for LAN host and headers. ✅ `.env` confirmed 2025-09-18.
   - Document current limitation (catalog only, no auto-execution) in WebUI runbook. ✅ Noted in `projects/litellm/CLAUDE.md`.
   - Capture output of `test-openwebui-mcp.sh` (even if failure) with explanation. ✅ Log stored at `projects/litellm/evaluation/test-openwebui-mcp-2025-09-18.log` (shows expected limitation).
3. **VS Code / Claude**
   - Create example `mcp_servers.json` referencing internal + external hosts. ✅ `projects/claude/config/mcp_servers.litellm.example.json` added 2025-09-18.
   - Add Windows credential storage guidance (Credential Manager / `%APPDATA%\codex\config.toml`). ✅ Documented in `projects/claude/CLAUDE.md`.

### Phase 4 – Documentation & Artifact Consolidation
1. Update `projects/litellm/MCP-INTEGRATION-STATUS.md` with Phase 1–3 findings.
2. Cross-reference updates in `projects/claude/config/mcp-settings.json` doc and any client runbooks.
3. Log validation artifacts (curl outputs, CLI transcript, WebUI script logs).

### Phase 5 – Outstanding Decisions
1. Coordinate with network/DNS team to expose `litellm.linuxserver.lan` (ports 80/443 open per `AINotes/network.md`); update `CODEXMCP.md` once resolution confirmed. ⚠️ Pending.
2. Decide on scoped API key issuance; recommended approach: issue per-client scoped keys via LiteLLM admin API once integration validated. Document process in `secrets/litellm.env` notes. ⚠️ Needs security approval.
3. Define trigger for onboarding additional MCP services (monitoring/n8n/timescaledb) after baseline validation. Suggested milestone: LiteLLM LAN route validated + Codex CLI tool invocation captured. ⚠️ Pending.

Execute phases sequentially or in parallel where practical; mark completion by updating checkboxes in `CODEXMCP.md` and filing artifacts as outlined.
