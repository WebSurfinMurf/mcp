# Postmortem: MCP Proxy Connection Failures (Resolved)

## Summary
Claude Code CLI reported `✘ failed` for the `postgres` and `fetch` servers even though `curl` tests against the MCP proxy succeeded. The issue was traced to the CLI configuration pointing at `http://localhost:9090/...`, which only works when the CLI runs on the same host as the proxy. When the CLI is launched from another workstation, `localhost` resolves to the local machine, so no requests ever reached the proxy.

## Corrective Actions
1. **Change advertised base URL** – Updated `config/config.template.json` so the proxy announces `http://linuxserver.lan:9090` instead of `http://localhost:9090`.
2. **Preserve service registrations** – Modified `render-config.sh` to merge existing `mcpServers` entries when re-rendering, preventing accidental removal during token rotations.
3. **Provide CLI sync script** – Added `sync-claude-config.sh`, which reads the token from `/home/administrator/secrets/mcp-proxy.env` and writes `~/.config/claude/mcp-settings.json` with `linuxserver.lan` URLs.
4. **Sanitised documentation** – Removed hard-coded bearer tokens from status docs and refreshed the Claude runbook to reference the new workflow.

## Verification Steps
- Re-rendered config: `./render-config.sh` (kept existing `postgres` and `fetch` entries).
- Synced Claude config: `./sync-claude-config.sh` (generated config using LAN hostname).
- Validate from a workstation: `curl -N -H 'Accept: text/event-stream' -H "Authorization: Bearer $MCP_PROXY_TOKEN" http://linuxserver.lan:9090/postgres/sse` (should return `HTTP/1.1 200 OK`).
- After syncing, Claude CLI `/mcp` should show `postgres-proxy` and `fetch-proxy` as `✔ connected` when run off-box.

## Lessons Learned
- Always advertise LAN-accessible hostnames (`linuxserver.lan`) for shared services; avoid `localhost` unless the client runs on the same machine.
- Regeneration scripts must preserve dynamic service registrations to prevent regression during credential rotation.
- Shipping a helper script (`sync-claude-config.sh`) reduces configuration drift and keeps secrets out of version control.
