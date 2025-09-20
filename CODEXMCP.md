# Codex MCP Integration Plan (Revised)

**Owner**: Codex  
**Updated**: 2025-09-18  
**Objective**: Integrate upstream MCP servers (postgres, filesystem, future monitoring) with LiteLLM’s native MCP gateway while keeping downloaded packages unmodified, and expose the resulting tools to Codex CLI, Open WebUI, and remote VS Code clients.

---

## 1. Baseline & Constraints

- LiteLLM container (`litellm-custom:latest`) runs v1.77.1, matching the minimum referenced in prior MCP work.
- Upstream MCP projects are stored under `projects/mcp/*/source`; do **not** edit their contents. All execution must invoke the shipped stdio/HTTP entrypoints.
- Traefik must publish both `litellm.ai-servicers.com` (Keycloak-protected) and `litellm.linuxserver.lan` (LAN-only) so internal tooling bypasses SSO when required.
- LiteLLM enforces authentication. Every `/mcp` call needs a `Bearer` API key and an `x-mcp-servers` selector header.
- LiteLLM relays MCP tool catalogs and invocation payloads but does not execute chained actions; clients (or future middleware) must handle side effects.

---

## 2. Gap Review (Original Plan vs Current Reality)

| Requirement | Planned Behaviour | Current Observation | Needed Adjustment |
|-------------|-------------------|---------------------|-------------------|
| Unmodified upstream MCP binaries | `npx postgres-mcp`, `npx mcp-server-filesystem` executed directly | ✅ LiteLLM config still references upstream packages | None |
| Dual-host LiteLLM routing | Traefik routes for Internet + LAN | 🔧 External route active; LAN route recently re-added but lacking documentation/testing | Document and verify `litellm.linuxserver.lan` |
| `/mcp/tools` discovery | Works for authenticated clients | ❌ Auth failures seen when Bearer prefix missing | Fix client configs, add verification steps |
| Client coverage (Codex CLI, Open WebUI, VS Code) | All target LiteLLM MCP | Partial: CLI still points to external host; Open WebUI uses HTTPS; VS Code remote lacks guidance | Update runbooks + configs |

---

## 3. Phased Execution Plan

### Phase A – LiteLLM Routing Validation
- [ ] Confirm Traefik labels expose both `litellm.ai-servicers.com` and `litellm.linuxserver.lan` (see `projects/litellm/docker-compose.yml`).
- [x] Verify LAN access: `curl -sS -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H 'x-mcp-servers: mcp_postgres,mcp_filesystem' http://litellm.linuxserver.lan/mcp/tools` → expect an SSE stream containing tool catalog events. _(2025-09-18: executed on LinuxServer via `test-lan-mcp-tools.sh`; see `projects/litellm/evaluation/lan-mcp-tools-2025-09-18-075003.log` showing heartbeat pings)_
- [ ] Note LAN usage requirements in `projects/litellm/CLAUDE.md` and service runbooks.

### Phase B – MCP Server Registration (Upstream Only)
- [ ] Ensure `projects/litellm/config.yaml` keeps stdio definitions:
  ```yaml
  mcp_servers:
    mcp_postgres:
      transport: "stdio"
      command: "postgres-mcp"
    mcp_filesystem:
      transport: "stdio"
      command: "mcp-server-filesystem"
  ```
- [ ] Secrets: confirm `secrets/mcp-postgres.env` + `secrets/litellm.env` expose `POSTGRES_MCP_URL` and `FILESYSTEM_ALLOWED_PATHS` without hardcoding in code.
- [ ] Restart LiteLLM (no rebuild) when secrets/config change.

### Phase C – Client Configuration Matrix
- **Codex CLI (LinuxServer)**
  - [ ] Point `~/.codex/config.toml` to `http://litellm.linuxserver.lan/mcp/` and ensure the `Authorization` value includes the `Bearer ` prefix.
  - [ ] Configure persistent headers so the CLI sends `x-mcp-servers = "mcp_postgres,mcp_filesystem"` (or the desired alias set).
  - [ ] Validate with `codex mcp list` and sample tool invocations. _(2025-09-18: list command OK; tool invocation awaits interactive workflow – see `projects/litellm/evaluation/codex-cli-mcp-2025-09-18.txt`)_
- **Open WebUI**
  - [ ] Set `OPENAI_API_BASE_URL=http://litellm.linuxserver.lan/v1` in `secrets/open-webui-internal.env`.
  - [ ] Ensure the WebUI passes `x-mcp-servers` when invoking `/mcp/tools`; document limitations because LiteLLM currently returns streaming catalogs without executing follow-on tool actions. _(2025-09-18: `archive/test-openwebui-mcp.sh` produced "Error or no response" for every probe; log saved to `projects/litellm/evaluation/test-openwebui-mcp-2025-09-18.log`)_
- **VS Code (Remote Windows)**
  - [ ] Provide `mcp_servers.json` example referencing internal host (VPN/tunnel) and external host (Keycloak) as fallbacks. _(2025-09-18: example committed as `projects/claude/config/mcp_servers.litellm.example.json`)_
  - [ ] Document how to store API keys securely on Windows (Credential Manager or `%APPDATA%\.codex\config.toml`). _(2025-09-18: guidance captured in `projects/claude/CLAUDE.md` under "MCP Client Guidance")_

### Phase D – Validation & Documentation
- [ ] Extend or parameterize `projects/litellm/test-mcp-integration.py` to target the LAN hostname; capture output.
- [ ] Monitor LiteLLM logs (`docker logs litellm --tail 100`) for residual auth errors.
- [ ] Update `projects/litellm/MCP-INTEGRATION-STATUS.md` with the new validation results and note that MCP execution path is now confirmed. _(2025-09-18: initial status record created with current blockers noted)_

---

## 4. Compatibility & Future Enhancements

- Additional MCP services (monitoring, n8n, timescaledb) must follow the same pattern: clone upstream, invoke via stdio/HTTP, register with zero local modifications.
- If LiteLLM adds native MCP execution hooks in newer versions, re-evaluate upgrading after current plan passes validation.
- Consider issuing per-team API keys (rather than master key) once the flow is stable; track in `secrets/litellm.env`.

---

## 5. Deliverables Checklist

- [ ] LAN + internet routing verified and documented.
- [ ] LiteLLM `/mcp/tools` returns tool catalog when called with proper headers.
- [ ] Codex CLI, Open WebUI, and VS Code remote instructions/configs updated and tested.
- [ ] Validation artifacts (test outputs/log excerpts) stored under project control.
- [ ] Documentation refreshed: `projects/litellm/CLAUDE.md`, `projects/claude/config/mcp-settings.json`, and any client runbooks.

---

## 6. Outstanding Questions

1. Document firewall allowances so Windows desktops on the LAN can reach `litellm.linuxserver.lan` without tunneling.
2. Should we generate scoped API keys for MCP usage instead of sharing the master key? Requires coordination with secrets management.
3. Timeline for enabling additional MCP services (monitoring, n8n) once postgres/filesystem integrations are validated?

Provide answers before advancing beyond Phase B so the implementation remains aligned with the “no local modifications” principle.
