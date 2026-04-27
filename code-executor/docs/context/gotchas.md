# Gotchas

Non-obvious behaviors and traps. Add new entries at the top.

---

## Vanilla MCPSTANDARD §3c `in_group()` only checks supplementary group members, missing primary-group members
Symptom: wrapper exits with `FATAL: <user> not in administrators or developers` even though `id -Gn` shows the user is in the role group.
Cause: `getent group administrators` returns `administrators:x:2000:` with empty 4th (members) field — `administrator` user has `administrators` as **primary** group (GID 2000), not supplementary. The standard's awk-based check only walks the 4th field.
Fix: `mcp-code-executor` wrapper checks `[[ "$(id -gn "$REAL_USER")" == "$1" ]]` first, then falls through to the supplementary loop. Documented at MIGRATION-TO-MCPSTANDARD.md §10. Pending promotion back into MCPSTANDARD §3c canonical text.

## Vanilla `/run/secrets` mount with `chmod 0644` / `group_add` leaks both keyfiles to user-supplied code in `execute_code`
Symptom: developer-role caller can use `execute_code` to read the admin keyfile, escalating to admin role.
Cause: `executor.ts` (long-lived, runs as `1000:1000`) and any user code spawned via `execute_code` share the container UID with mcp-server.ts. If the container UID can read `/run/secrets/*`, so can user code.
Fix: per-call `docker exec --user "1000:${ROLE_GID}"` so mcp-server.ts runs with effective GID = role group; the long-lived `executor.ts` (1000:1000) and user code cannot read either keyfile. Verified empirically — see MIGRATION-TO-MCPSTANDARD.md §10. Pending promotion into MCPSTANDARD §3a/§3c.

## `mcp-server.ts` runs under `tsx` in ESM mode — `require()` is undefined
Symptom: `MCP_KEY_FILE set but unreadable: ... ReferenceError: require is not defined`.
Cause: `tsx` defaults to ESM for `.ts` files; CommonJS `require('fs')` doesn't work.
Fix: `import { readFileSync } from 'node:fs'` at the top of `mcp-server.ts`. Same pattern applies to any future synchronous filesystem reads added at startup.

## Editing `~/.claude.json` doesn't affect already-spawned MCP children
Symptom: changed wrapper command in `~/.claude.json` but Claude Code still uses the old one.
Cause: stdio MCPs spawn once at session start; in-flight session keeps its already-spawned child. The configuration is only re-read on next session start.
Fix: `/exit` and re-launch Claude Code to pick up the new wrapper.

## tmpfs mounted as root after fresh deploy
Symptom: container can't write to `/workspace` or `/tmp/executions`.
Cause: Docker mounts tmpfs as root; container user `node` (UID 1000) can't write.
Fix: `docker exec -u root mcp-code-executor chown -R node:node /workspace /tmp/executions` after every fresh deploy. Future fix: configure tmpfs `uid=1000,gid=1000` in `docker-compose.yml`.

## `deploy.sh` health-check still curls `http://localhost:9091/health`
Symptom: deploy reports "❌ Service failed health check" with logs dump, but container is actually fine.
Cause: host port `9091:3000` was dropped 2026-04-27 (MCPSTANDARD §3a compliance). `deploy.sh` line 34 wasn't updated.
Workaround: ignore the false-negative; verify health via `docker exec mcp-code-executor wget -qO- http://localhost:3000/health` instead. Real fix: update `deploy.sh` to use `docker exec`.

## Container UID 1000 reading `/run/secrets/*.key` requires GID match
Symptom: `head -c 8 /run/secrets/code-executor-administrator.key` returns "Permission denied" inside the container.
Cause: keyfiles are `0640 root:<role-group>` on host (e.g. `root:administrators` GID 2000). Inside the container, `node` user (GID 1000) is not in GID 2000 by default.
Fix (current pattern): `docker exec --user 1000:<role-gid>` for the MCP exec subprocess only. This gives the exec process GID 2000 (or 3000 for developer) so it can read the role's keyfile. The long-lived processes stay at `1000:1000` and cannot read keys (intentional).
Misuse to avoid: do NOT add `group_add: ["2000","3000"]` to compose, do NOT chmod 0644 on host keyfiles — both leak both keys to user code.
