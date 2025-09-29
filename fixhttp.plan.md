# TBXark Streamable HTTP Remediation Plan

## Source Feedback
Selected guidance: forensic report pointing to mis-mounted config path and missing `/config/config.json` expectations.

## Objectives
1. Mount proxy configuration to `/config/config.json` and simplify startup flags.
2. Verify proxy loads config, registers `filesystem`, and serves `/filesystem/mcp` without 404.
3. Adjust `baseURL` and other fields for external client reachability.
4. Document validation evidence (curl, logs) and update status notes.

## Steps
1. **Compose Fix**
   - Update `mcp/proxy/docker-compose.yml` volume to `./config.json:/config/config.json:ro`.
   - Remove explicit `-config /config.json` override or align with `/config/config.json`.
   - Ensure health check uses existing binaries (`curl`).

2. **Configuration Review**
   - Confirm `config.json` includes `type: "streamable-http", baseURL` with reachable host.
   - Add optional `version` if required by current proxy schema.

3. **Redeploy & Validate**
   - `docker compose up -d --force-recreate` (host side).
   - Run updated `phase0-run.sh` (after adjusting to new mount) to capture logs.
   - Confirm initialize/tools/list return `200/202`, `Mcp-Session-Id`, and tool list.

4. **Documentation & Follow-up**
   - Record results in `mcp/fixhttp.md` and `mcp/planhttp.status.md`.
   - Note remaining TODOs (e.g., baseURL final value, client registration).

## Risks / Open Questions (to be proven)
- Proxy may require `version` field; need to confirm runtime expectations.
- If 404 persists, inspect `docker logs` for config read errors or fallback behavior.
