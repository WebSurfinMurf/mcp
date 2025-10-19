# MCP Integration Status – LiteLLM Gateway

**Updated**: 2025-09-18  
**Owner**: Codex

---

## Environment Snapshot
- **LiteLLM version**: 1.77.1 (container `litellm`)  
- **Internal host**: `http://litellm.linuxserver.lan` (Traefik HTTP entrypoint)  
- **External host**: `https://litellm.ai-servicers.com` (Keycloak-protected)  
- **Config**: `projects/litellm/config.yaml` registers upstream MCP servers via stdio (`postgres-mcp`, `mcp-server-filesystem`).  
- **Secrets**: `secrets/litellm.env` provides `LITELLM_MASTER_KEY`, `POSTGRES_MCP_URL`, and filesystem allowlist.  
- **Client configs**:  
  - Codex CLI (`~/.codex/config.toml`) → `http://litellm.linuxserver.lan/mcp/`  
  - Claude/VS Code (`projects/claude/config/mcp-settings.json`) → internal + external fallback  
  - Open WebUI internal env → `http://litellm.linuxserver.lan/v1`

Upstream MCP repos under `projects/mcp/*/source` remain untouched; LiteLLM launches them directly via stdio in line with `CODEXMCP.md`.

---

## Validation to Date
- **Traefik routing**: Split the LiteLLM ingress into two routers per host: `/ui`, `/docs`, `/swagger`, `/openapi.json` remain publicly accessible; all other paths require `Authorization: Bearer …` and now route via `HeaderRegexp` (Traefik v3-compatible). Confirmed with a temporary `whoami` test service before applying to production, then validated live using `curlimages/curl` containers on the `traefik-net` network.  
- **LAN access (SSE)**: `test-lan-mcp-tools-once.sh` / `mcp-diagnose.sh` continue to show `/mcp/tools` streaming heartbeat `ping` events only (latest capture `projects/litellm/evaluation/diagnostic-2025-09-19-071230-mcp-sse.log`). Tool catalogs still pending upstream MCP fixes.  
- **LiteLLM logs**: Added a Traefik middleware that injects the admin Bearer key for `/schedule/model_cost_map_reload/status`; the UI poll now succeeds (HTTP 400 when no job is queued) and the recurring `ProxyException` noise has stopped.  
- **Codex CLI**: configuration updated; awaiting interactive test (next step after context reload).  
- **Open WebUI**: manual prompt (“list my PostgreSQL databases”) returned standard textual guidance with no MCP `tool_calls`, confirming UI still treats LiteLLM as a vanilla LLM endpoint.

---

## Immediate Next Steps (per `CODEXMCP.md`)
1. **Codex CLI validation** – after restart, run an MCP-enabled prompt (e.g., “List my PostgreSQL databases”) and capture the transcript under `projects/litellm/evaluation/`.  
2. **SSE payload check** – determine why `/mcp/tools` only emits `ping`; confirm upstream servers are reachable or adjust LiteLLM config.  
3. **Documentation** – fold new CLI/Open WebUI artifacts into `MCP-INTEGRATION-STATUS.md` once collected.  
4. **Firewall note** – ensure Windows hosts on the LAN can reach `litellm.linuxserver.lan` (open ports 80/4000 as needed).  
5. **Execution layer (future)** – design the middleware required for LiteLLM/Open WebUI to execute returned tool calls.

Addendum: UI/docs assets remain open; everything else still needs `Authorization: Bearer …`. Traefik now injects the admin key for the schedule-status route—plan to swap in a scoped key so labels don’t expose the master credential.

---

## Outstanding Questions
- Should we mint scoped API keys for MCP users instead of relying on the master key?  
- Timeline for onboarding additional upstream MCP services (monitoring, n8n, timescaledb) once postgres/filesystem paths are validated?

Document answers in `projects/mcp/CODEXMCP.md` before expanding the deployment further.
