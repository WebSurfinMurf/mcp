# Architecture

## Components
- [IMPLEMENTED] **`mcp-code-executor`** Docker container — single shared executor, no host ports published. User `node` (1000:1000) by default; per-call `--user 1000:<role-gid>` for MCP exec subprocess only.
- [IMPLEMENTED] **`/usr/local/bin/mcp-code-executor`** — root-owned shared host wrapper. Resolves Linux group → role → keyfile, stamps `MCP_SENDER_NAME`, `docker exec`s into the container.
- [IMPLEMENTED] **`/usr/local/bin/mcp-dispatcher`** — root-owned single SSH entry-point for laptop keys. Allow-list = `code-executor` only. Routes by `SSH_ORIGINAL_COMMAND`.
- [IMPLEMENTED] **`mcp-server.ts`** (in container) — stdio MCP bridge. Reads `MCP_KEY_FILE` (path) preferentially, falls back to `CODE_EXECUTOR_API_KEY` (env). Calls `executor.ts` HTTP API for tool execution + role lookup.
- [IMPLEMENTED] **`executor.ts`** (in container) — Fastify HTTP API on container port 3000. Validates `X-API-Key` against `roles.json`. Long-lived; runs as `1000:1000`.
- [IMPLEMENTED] **`generate-wrappers.ts`** — generates 63 TypeScript wrappers for upstream MCP tools at `/workspace/servers/<server>/<tool>.ts` (used by `execute_code` sandbox).

## Server-local data flow
```
Claude Code (administrator|websurfinmurf)
  → /usr/local/bin/mcp-code-executor (group→role→keyfile)
  → docker exec --user 1000:<role-gid> mcp-code-executor npx tsx /app/mcp-server.ts
  → mcp-server.ts (reads MCP_KEY_FILE, calls executor.ts via http://localhost:3000)
  → executor.ts (validates X-API-Key against roles.json, dispatches tool calls to mcp-proxy)
  → MCP Proxy (TBXark, http://mcp-proxy:9090) → individual MCP servers
```

## Laptop data flow
```
Claude Code on laptop
  → ssh -T -o BatchMode=yes -i ~/.ssh/id_ed25519_mcp <user>@linuxserver.lan "mcp code-executor"
  → SSH multiplexed master (~/.ssh/cm-%h-%p-%r, ControlPersist 1h)
  → sshd matches authorized_keys line: restrict,command="/usr/local/bin/mcp-dispatcher",no-user-rc
  → mcp-dispatcher reads SSH_ORIGINAL_COMMAND, validates allow-list, exec mcp-code-executor
  → (then identical to server-local data flow above)
```

## Networks
- [IMPLEMENTED] `mcp-net` — container ↔ mcp-proxy and other MCPs.
- [IMPLEMENTED] `traefik-net` — container ↔ aiagentchat-gateway (chat tools), reviewboard, gitlab.
- [IMPLEMENTED] No host port publish (since 2026-04-27). Internal access only via `docker exec` or container-network DNS (`mcp-code-executor:3000`).

## Tier classification
- [IMPLEMENTED] **Tier 1** per `~/projects/CLAUDE.md` — internal admin/developer tooling, LAN/VPN only, no Keycloak/Traefik in the data path. Reference implementation of `MCPSTANDARD.md`.
