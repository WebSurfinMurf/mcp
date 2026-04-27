# Interfaces

## Wrapper interface — `/usr/local/bin/mcp-code-executor`

Inputs (env from caller):
- `SSH_CLIENT` (optional) — set by sshd when invoked via dispatcher; otherwise empty for server-local.
- All other env stripped/ignored — wrapper trusts only kernel-attested `id -un`.

Outputs (env injected into `docker exec`):
- `MCP_KEY_FILE=/run/secrets/code-executor-<role>.key` — path-not-bytes (security boundary).
- `MCP_SENDER_NAME=<user>@<linuxserver-local|peer-IP-via-ssh>` — server-stamped, never client-supplied.
- `MCP_ROLE=<administrator|developer>` — for downstream tooling.

Exit codes:
- `0` — exec'd into container successfully.
- `2` — FATAL on group resolution failure or unreadable keyfile.

## Dispatcher interface — `/usr/local/bin/mcp-dispatcher`

Inputs:
- `SSH_ORIGINAL_COMMAND` from sshd (forced via `command="..."` in `authorized_keys`).
- Expected literal form: `mcp <name>` (exactly two whitespace-separated tokens).

Allow-list (in script):
- `code-executor` only (as of 2026-04-27). Extend by editing the `case` block, not by adding new authorized_keys lines.

Defense-in-depth:
- Scrubs all `MCP_*` env at start (defends against `AcceptEnv`).
- `IFS=$' \t\n'` to defeat IFS-injection.

Exit codes:
- Exec into the target wrapper on success.
- `2` — FATAL on missing/extra args, unknown target.

## MCP server (container) — `/app/mcp-server.ts`

Reads at startup:
1. `MCP_KEY_FILE` (path) → reads file, trims trailing newlines, uses as API key. (Preferred.)
2. `CODE_EXECUTOR_API_KEY` (raw bytes in env) → fallback for backwards compatibility during cutover.

Calls executor.ts:
- `GET /roles?key=<api-key>` → returns `{ name, allowed_mcp_tools, allowed_servers }`. Filters tool list before exposing to Claude Code.
- `POST /execute`, `POST /reviewboard/dispatch`, `POST /chat/send`, `GET /chat/read`, `GET /chat/who`, `POST /gitlab/create-issue`, `POST /gitlab/create-board`, `GET /tools/search`, `GET /tools/info/:server/:tool`, `GET /health` — all gated by `X-API-Key` header.

Stdio MCP tools exposed (12):
- `execute_code`, `search_tools`, `get_tool_info`, `list_mcp_tools`
- `dispatch_to_reviewboard`, `reviewboard_health`
- `chat_send`, `chat_read`, `chat_who`
- `create_gitlab_issue`, `create_gitlab_board`

## Executor HTTP API (container port 3000)

Authenticated by `X-API-Key` header (validated against `roles.json` SHA-256 entries).
- `GET /health` — version, uptime, server count, tool count by server. Public (no key).
- `GET /tools` — list of available tools (filtered by role).
- `GET /tools/search?query=&server=&detail=` — progressive disclosure (token efficiency).
- `GET /tools/info/:server/:tool?detail=` — single-tool info.
- `POST /execute` — body `{code, timeout?}` → executes TypeScript/Python in tmpfs sandbox.
- `POST /reviewboard/dispatch` — body `{prompt, target, timeout?, working_dir}` → dispatches to gemini/codex/claude review-board node.
- `GET /reviewboard/health` — node health.
- `POST /chat/send`, `GET /chat/read?count=`, `GET /chat/who` — Matrix chat passthrough.
- `POST /gitlab/create-issue`, `POST /gitlab/create-board` — GitLab API passthrough using `GITLAB_TOKEN_ADMIN` from container env.

## Keyfile contract

- Path on host: `/home/administrator/projects/secrets/code-executor-<role>.key`.
- Path in container: `/run/secrets/code-executor-<role>.key` (RO bind mount of the secrets dir).
- Format: 64 hex chars, **no trailing newline**.
- Mode: `0640`, owner `root:<role-group>` (`administrators` GID 2000 / `developers` GID 3000).
- `roles.json` maps SHA-256 of trimmed bytes → role name.
- Role names in `roles.json`: `admin` (legacy) and `developer`. Wrapper uses `administrator`/`developer` for the keyfile name (singular per MCPSTANDARD §3b).
- Backwards-compat symlink `code-executor-admin.key → code-executor-administrator.key` kept until 2026-05-04 minimum.

## roles.json (mounted RO at `/app/roles.json`)

```json
{
  "keys": { "<sha256-hex>": "admin|developer", ... },
  "roles": {
    "admin":     { "allowed_servers": ["*"], "allowed_mcp_tools": ["*"] },
    "developer": { "allowed_servers": ["postgres","playwright","openmemory","minio","ib","timescaledb","vikunja"],
                   "allowed_mcp_tools": [<11 of 12 tools, no execute_code restrictions> ] }
  }
}
```
