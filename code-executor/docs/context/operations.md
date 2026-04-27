# Operations

## Deploy
```bash
cd /home/administrator/projects/mcp/code-executor && ./deploy.sh
```
- Loads `~/projects/secrets/gitlab.env` and `~/projects/secrets/code-executor.env`.
- `docker compose build && docker compose up -d`.
- Health check on `http://localhost:9091/health` ← **broken since 2026-04-27 port drop**; `deploy.sh` line 34 needs migration to `docker exec mcp-code-executor curl -sf http://localhost:3000/health` or removal. (Deployment still completes successfully despite the failed curl — it's just a misleading "healthy/unhealthy" report at the end of deploy.)
- After fresh deploy, fix tmpfs perms: `docker exec -u root mcp-code-executor chown -R node:node /workspace /tmp/executions`.

## Container details
- Container name: `mcp-code-executor`. Image built from local `Dockerfile` (Node 20 alpine + Python 3 + tsx + npm).
- Restart policy: `unless-stopped`.
- Networks: `mcp-net`, `traefik-net` (both external, must exist).
- No host ports published since 2026-04-27. Internal access via `docker exec` or `mcp-code-executor:3000` from other containers on the same network.
- Container user: `1000:1000` (`node`). Group_add: `127` (host docker GID).
- Tmpfs: `/tmp/executions` (100MB, noexec/nodev/nosuid).

## Wrapper / dispatcher install
Both root-owned `0755` in `/usr/local/bin/`. Source-of-truth copies live at `/tmp/claude-2000/mcpmigrate/` during the migration session; for permanent storage, future maintenance edits can stage to `~/projects/mcp/code-executor/host-bin/` and `sudo install` into `/usr/local/bin/`.

```bash
sudo install -m 0755 -o root -g root <staged-file> /usr/local/bin/mcp-{code-executor,dispatcher}
```

## Restart Claude Code (post-migration)
Editing `~/.claude.json` changes only NEW Claude Code sessions. Existing sessions keep their already-spawned MCP child until `/exit` and re-launch.

## Adding a new MCP under the same standard
1. Build container with `MCP_KEY_FILE` support, no published ports, secrets mount RO at `/run/secrets/`, role-aware UID enforcement.
2. Generate keys: `openssl rand -base64 32 | tr -d '\n' > /home/administrator/projects/secrets/<mcp-name>-<role>.key && chmod 0640 && chown root:<role-group>`.
3. Compute SHA-256 of trimmed bytes; register in container's `keys.json`.
4. Install `/usr/local/bin/mcp-<name>` (root-owned 0755) — clone `mcp-code-executor` and adjust container name + entry-point.
5. Add `<name>` to `mcp-dispatcher`'s allow-list `case` block.
6. Add `~/.claude.json` block (server-local: `"command": "/usr/local/bin/mcp-<name>"`; laptop: `"command": "ssh", "args": [..., "mcp <name>"]`).

## Key rotation
1. Generate replacement: `openssl rand -base64 32 | tr -d '\n' > /tmp/newkey`.
2. Add new SHA-256 to `roles.json`, redeploy (or mount `keys.json` from secrets/ to decouple).
3. `mv /tmp/newkey /home/administrator/projects/secrets/code-executor-<role>.key && chmod 0640 && chown root:<role-group>`.
4. `docker compose restart mcp-code-executor`. In-flight tool calls fail once; clients reconnect.
5. After all clients reconnect (next session), remove old SHA-256 from `roles.json` and redeploy.

## Key revocation (lost laptop)
1. `sudo sed -i '/<comment-of-laptop-key>/d' /home/<user>/.ssh/authorized_keys`.
2. Optionally rotate the role keyfile if the laptop also had non-MCP access.
3. `journalctl -t mcp-dispatcher --since '7 days ago' | grep <client-IP>` to audit prior usage.

## Cleanup deadlines
- After 1 week of stable operation (~2026-05-04): delete `~administrator/.claude/skills/mcp-wrapper.sh.deprecated.2026-04-27` and the websurfinmurf equivalent.
- After 1 week (~2026-05-04): delete the backwards-compat symlink `code-executor-admin.key → code-executor-administrator.key` if no logs reference the old name.

## Key files
- Source: `mcp-server.ts`, `executor.ts`, `client.ts`, `generate-wrappers.ts`, `Dockerfile`, `docker-compose.yml`, `package.json`, `roles.json`, `deploy.sh`.
- Migration record: `MIGRATION-TO-MCPSTANDARD.md` (especially §10 — completion record + deviations).
- Refocus history: `docs/refocus/`.
