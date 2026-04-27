# code-executor migration to mcpstandard.md v3

**Audience:** the next Claude Code session that picks this up at `~/projects/mcp/`.
**Authored by:** administrator-claude · 2026-04-26 (investigation only, no code changed).
**Goal:** migrate the running `mcp-code-executor` service to the v3 platform standard so it's the reference implementation for every other MCP, including agent-memory.

**Canonical standard:** `~/projects/mcp/MCPSTANDARD.md` (also at `/mnt/shared/mcpstandard.md`).

This file is the gap analysis + step-by-step migration plan. The standard itself is the contract; this file is the diff between today and that contract.

---

## 1. Current state (what's actually running)

### 1a. Wrapper
- Location: `~administrator/.claude/skills/mcp-wrapper.sh` AND `~websurfinmurf/.claude/skills/mcp-wrapper.sh` — **per-user duplicates** (DRY violation; two places to patch).
- Owned by the invoking user (not root). Group resolution by `id -Gn | grep -qw administrators|developers`.
- Reads key file with `cat`, exports as `CODE_EXECUTOR_API_KEY` env var, then `docker exec -e CODE_EXECUTOR_API_KEY="$KEY" mcp-code-executor npx tsx /app/mcp-server.ts`.
- **No logging.** Wrapper is silent on every invocation.

### 1b. Key files
- `/home/administrator/projects/secrets/code-executor-admin.key` (mode `0640`, owner `administrator:administrators`).
- `/home/administrator/projects/secrets/code-executor-developer.key` (mode `0640`, owner `administrator:nogroup` — should be `administrator:developers`; current group is wrong).
- 64 bytes each, **no trailing newline** (already canonical — good).
- The 64-char hex string IS the API key; `roles.json` inside the container maps `sha256(key)` → role. (So the file content is the secret; the hash is what's registered.)

### 1c. Container (`mcp-code-executor`)
- Compose file at `~/projects/mcp/code-executor/docker-compose.yml`.
- **Publishes port `9091:3000`** to the host. The standard says no host ports — but the published port is consumed by other services (the executor's HTTP API for `code-executor-stdio.py` etc.). Don't blindly remove; see §3 below.
- Mounts `roles.json` at `/app/roles.json` (RO), `/var/run/docker.sock` (RO), `/etc/localtime` (RO).
- Runs as user `1000:1000` with `group_add: ["127"]` (host docker GID).
- `mcp-server.ts` reads `CODE_EXECUTOR_API_KEY` from env, queries its own backend `/roles?key=...` to resolve role.

### 1d. Claude Code config
- `~/.claude.json` (administrator) — `code-executor` block points to `/home/administrator/.claude/skills/mcp-wrapper.sh`.
- Same pattern in `~websurfinmurf/.claude.json`.

### 1e. Laptop access
- **None today.** No laptop pubkey in `~administrator/.ssh/authorized_keys` or `~websurfinmurf/.ssh/authorized_keys` (only CI runner keys are there). Laptop sessions can't reach this MCP.

### 1f. Audit logs
- None at the wrapper layer.
- Container logs MCP-tool execution (via the executor backend's own logs).
- No `mcp-dispatcher` exists yet.

---

## 2. Gap vs v3 standard

| § | What v3 wants | What we have | Severity |
|---|---|---|---|
| 3a | No host ports published | Publishes `9091:3000` | **Investigate first** — see §3. May be intentional for non-MCP HTTP consumers. |
| 3a | Secrets dir mounted RO at `/run/secrets/` | Not mounted | Add mount |
| 3a | Container reads `MCP_KEY_FILE` (path), validates SHA-256 + constant-time | Container reads `CODE_EXECUTOR_API_KEY` (raw key value) | Add MCP_KEY_FILE support |
| 3b | Role suffix `-administrator` (singular) / `-developer` | `-admin` (different word) / `-developer` | Rename + symlink for cutover |
| 3b | Owner `root:<role-group>` | Owner `administrator:administrators` and `administrator:nogroup` | Re-chown |
| 3b | Mode `0640` | `0640` ✓ | OK |
| 3b | No trailing newline | No trailing newline ✓ | OK |
| 3c | Wrapper at `/usr/local/bin/mcp-code-executor`, root-owned, shared | Per-user `~/.claude/skills/mcp-wrapper.sh` | Relocate, dedupe |
| 3c | Group resolution via `getent group` + literal compare | `id -Gn \| grep -qw` (whole-word bug on hyphenated groups) | Replace |
| 3c | Stamps `MCP_SENDER_NAME` server-side | Not set | Add |
| 3c | Passes `MCP_KEY_FILE` (path), not key bytes | Passes `CODE_EXECUTOR_API_KEY` (key bytes) | Switch delivery mode |
| 3c | `logger -t mcp-code-executor` audit line | None | Add |
| 3d | Dispatcher at `/usr/local/bin/mcp-dispatcher` (allow-list, env scrub, audit log) | Doesn't exist | Create |
| 3e | Server-local config points at `/usr/local/bin/mcp-code-executor` | Points at per-user wrapper | Update both `~/.claude.json` files |
| 3f | Laptop config uses `ssh -T ... "mcp code-executor"` | N/A (no laptop access today) | Add when laptop comes in |
| 3g | Laptop multiplexing block, ControlPersist 1h, %h-%p-%r path, local-FS only | N/A | Add on laptop |
| 3h | `restrict,command="/usr/local/bin/mcp-dispatcher",no-user-rc` in authorized_keys | No laptop key present | Add laptop key when ready |

**Existing bugs the migration cleans up:**
- `developer.key` group ownership is `nogroup` instead of `developers` — `id -Gn | grep -qw developers` happens to work because the GROUP `developers` exists and the user is in it, but the keyfile permissions are wrong: any user in `nogroup` (effectively many service accounts) could read the developer key. **This is a real bug today.**
- Per-user wrapper duplication means a fix to one wrapper doesn't apply to the other.

---

## 3. Open question: published port `9091:3000`

The standard says "no host ports published" — but `mcp-code-executor` publishes `9091:3000` and *something* on the host or LAN may rely on it (other Compose stacks, monitoring, manual scripts).

**Before §4 step 7, find every consumer:**
```bash
sudo ss -tnp '( dport = :9091 )'                 # active connections
sudo grep -rE 'localhost:9091|:9091|9091/' /home/administrator/projects/ \
  --include='*.yml' --include='*.yaml' --include='*.env' --include='*.sh' --include='*.py' --include='*.ts'
```

Findings determine the path:
- **No external consumers** → drop the port publish, fully comply with §3a.
- **Internal Docker consumers only** (other containers reaching `mcp-code-executor:3000` via shared network) → drop the host-port publish; container-to-container traffic still works via the docker network. Check that all consumers are on `mcp-net` or `traefik-net`.
- **Host consumers** (something on the host calling `localhost:9091`) → either move them onto a docker network, or accept this MCP as a §3a exception until they're migrated. **Don't pretend it's compliant when it isn't.**

This is an investigation step, not a fix; do it before touching the compose file.

---

## 4. Migration steps (server-side first)

Each step is reversible until step 8. Take a backup of every file you edit.

**Pre-flight:**
- `git status` in `~/projects/mcp/code-executor/` should be clean before starting.
- Verify Claude Code current session has working `mcp__code-executor__chat_who` so we have a baseline to re-test against.
- Snapshot current key files: `cp /home/administrator/projects/secrets/code-executor-*.key /tmp/codex-keys-backup-$(date +%s)/`.

**Step 1 — Fix keyfile ownership and naming (independent prerequisite).**
- `sudo chown root:developers /home/administrator/projects/secrets/code-executor-developer.key` (fixes `nogroup` bug).
- `sudo chown root:administrators /home/administrator/projects/secrets/code-executor-admin.key`.
- Rename `code-executor-admin.key` → `code-executor-administrator.key` (matches §3b singular-role convention). Leave a symlink at the old name during cutover so nothing breaks: `sudo ln -s code-executor-administrator.key /home/administrator/projects/secrets/code-executor-admin.key`.

**Step 2 — Container support for `MCP_KEY_FILE`.**
- In `mcp-server.ts`, add: if `MCP_KEY_FILE` is set, read its contents (trimmed) and use as `API_KEY`; otherwise fall back to `CODE_EXECUTOR_API_KEY`. Both paths supported during cutover.
- In `docker-compose.yml`, add the secrets mount:
  ```yaml
  volumes:
    - /home/administrator/projects/secrets:/run/secrets:ro
    # ... (existing mounts)
  ```
- Rebuild and redeploy: `cd ~/projects/mcp/code-executor && ./deploy.sh`.
- Smoke test from inside the container that `cat /run/secrets/code-executor-administrator.key` works (UID 1000 needs read access — keyfile is mode 0640 root:administrators; UID 1000 is NOT in administrators inside the container, so this WILL fail). **Decision: either chmod 0644 (gives world-read inside the container, which is fine — only the container can see /run/secrets), or add the relevant group inside the image.** Recommend `0644` on the keyfile copy mounted into containers; defense-in-depth for that key is the host directory perms, not the container's view. Or split: keep host `0640`, mount via per-role `tmpfs` of just the file the container needs. Simplest: mount only the role's keyfile, not the whole secrets dir.
  - **Recommended pattern:** `--mount type=bind,src=/home/administrator/projects/secrets/code-executor-administrator.key,dst=/run/secrets/code-executor-administrator.key,ro`. But compose can't conditionally mount by role at exec time. So mount the whole dir RO at `/run/secrets/`, and accept that the container UID can read both role keyfiles. The wrapper still tells it which one to use via `MCP_KEY_FILE`. The trust boundary is: whoever can `docker exec` chooses the role anyway (per §5 of the standard).

**Step 3 — Install the dispatcher.**
- Create `/usr/local/bin/mcp-dispatcher` per `MCPSTANDARD.md` §3d. Allow-list starts as `code-executor` only.
- `sudo chown root:root /usr/local/bin/mcp-dispatcher && sudo chmod 0755 /usr/local/bin/mcp-dispatcher`.

**Step 4 — Install the shared wrapper.**
- Create `/usr/local/bin/mcp-code-executor` per `MCPSTANDARD.md` §3c, parameterised for the container name `mcp-code-executor` and the entry-point `npx tsx /app/mcp-server.ts`.
- `sudo chown root:root /usr/local/bin/mcp-code-executor && sudo chmod 0755`.
- Smoke test directly: `/usr/local/bin/mcp-code-executor < /tmp/init-request.json` should respond. Where `init-request.json` is a minimal MCP `initialize` JSON-RPC payload.

**Step 5 — Update server-local Claude Code configs.**
- In `~administrator/.claude.json`, change the `code-executor.command` to `/usr/local/bin/mcp-code-executor` and clear `args`.
- Same in `~websurfinmurf/.claude.json`.
- Restart Claude Code (`/exit` and re-launch).
- Verify `claude mcp list` shows `code-executor: Connected`.
- Run `mcp__code-executor__chat_who` — should succeed; the audit log (`journalctl -t mcp-code-executor`) should record the call.

**Step 6 — Decommission per-user wrappers.**
- Once both users have been verified on the new shared wrapper, `sudo mv ~administrator/.claude/skills/mcp-wrapper.sh ~administrator/.claude/skills/mcp-wrapper.sh.deprecated.YYYY-MM-DD` (and same for websurfinmurf).
- Don't delete; symlink-rot risk during the cutover window. Delete after a week of stable operation.

**Step 7 — (Conditional, depends on §3 outcome) drop the host port publish.**
- Only after §3 confirms no external consumers.
- Edit `docker-compose.yml`, remove `- "9091:3000"` from `ports:`.
- `./deploy.sh` to redeploy.
- Verify `ss -tnp '( sport = :9091 )'` shows nothing on the host.

**Step 8 — Laptop side (when ready).**
- On the laptop:
  - Generate dedicated keypair: `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_mcp -C "<user>@<device>-mcp"`.
  - Add the multiplexing block to `~/.ssh/config` per standard §3g.
  - Add `code-executor` block to `~/.claude.json` per standard §3f.
- On the server:
  - Append the laptop pubkey to `~administrator/.ssh/authorized_keys` (or `~websurfinmurf/.ssh/authorized_keys` depending on which account the laptop will use) with the `restrict,command="/usr/local/bin/mcp-dispatcher",no-user-rc` prefix.
- From the laptop, run all five §8 verification tests in `MCPSTANDARD.md`:
  1. Positive: `ssh -T -o BatchMode=yes <user>@linuxserver.lan "mcp code-executor"` opens with `initialize` response.
  2. Negative: `ssh -T <user>@linuxserver.lan ls /` MUST be rejected. **If this returns a directory listing, STOP** — the `restrict,command="..."` line is wrong.
  3. Cold-start: wait > ControlPersist, then `claude mcp list` succeeds.
  4. Master socket: `ls -l ~/.ssh/cm-*` shows a Unix socket after first call.
  5. Key offered: `ssh -v ... 2>&1 | grep 'Offering\|Authenticated'` confirms `id_ed25519_mcp` is the one used.

**Step 9 — Document the new state.**
- Update `~/projects/mcp/code-executor/CLAUDE.md` to point at this migration doc and `MCPSTANDARD.md` for canonical reference.
- Add an entry to `~/projects/CLAUDE.md` master index mentioning that code-executor is the reference implementation of the Tier-1 MCP standard.

---

## 5. Rollback plan

If anything goes wrong at any step before §4-8:
- Revert `~administrator/.claude.json` and `~websurfinmurf/.claude.json` to the wrapper paths in `~/.claude/skills/`.
- Restart Claude Code.
- The original wrappers and key files are unchanged (we only added new ones); old path keeps working.

If §4-8 (laptop SSH) breaks:
- Remove the laptop's pubkey line from `~/.ssh/authorized_keys`.
- Clear the laptop's `~/.ssh/cm-*` sockets (`rm ~/.ssh/cm-*`).
- Server-local sessions are unaffected.

---

## 6. Test matrix (definition of done)

Server-local — administrator:
- [ ] `claude mcp list` shows `code-executor: Connected`.
- [ ] `mcp__code-executor__chat_who` returns expected sender name `administrator@linuxserver-local`.
- [ ] `journalctl -t mcp-code-executor --since '5 minutes ago'` shows one ACCEPT line per invocation.
- [ ] `journalctl -t mcp-dispatcher` is **empty** for server-local invocations (server-local bypasses dispatcher).

Server-local — websurfinmurf:
- [ ] Same as above but resolves to `developer` role.
- [ ] `mcp__code-executor__chat_who` returns sender `websurfinmurf@linuxserver-local`.
- [ ] Audit log shows `role=developer`.

Laptop — websurfinmurf:
- [ ] All five §8 verification tests pass.
- [ ] `mcp__code-executor__chat_who` returns `websurfinmurf@<laptop-IP>-via-ssh`.
- [ ] `journalctl -t mcp-dispatcher` shows ACCEPT for `target=code-executor`.
- [ ] `journalctl -t mcp-code-executor` shows the wrapper's audit line right after.

Negative tests:
- [ ] `ssh -T <user>@linuxserver.lan ls /` is rejected with FATAL.
- [ ] `ssh -T <user>@linuxserver.lan "mcp nonexistent"` is rejected with FATAL.
- [ ] `ssh -T <user>@linuxserver.lan "rm -rf /"` is rejected with FATAL.

---

## 7. After code-executor is the reference implementation

- agent-memory build adopts the same wrapper/dispatcher/keyfile pattern from R1 — no per-MCP transport reinvention.
- Future MCPs (any new ones in `~/projects/mcp/`) just need: container with `MCP_KEY_FILE` support, two key files in `secrets/`, one wrapper at `/usr/local/bin/mcp-<name>`, one entry added to dispatcher's allow-list, two `~/.claude.json` blocks. ~30 minutes per new MCP.

---

## 8. What's NOT in scope of this migration

- Replacing `roles.json` with anything else — keep the role/key/tool model exactly as-is.
- Changing what tools `code-executor` exposes.
- Changing the `dispatch_to_reviewboard` flow or the chat gateway.
- Migrating any other MCP (filesystem, postgres, playwright, etc.) — those are follow-on work, not this ticket.

---

## 9. Files and locations referenced

| Thing | Path |
|---|---|
| Canonical standard | `~/projects/mcp/MCPSTANDARD.md` |
| This migration doc | `~/projects/mcp/code-executor/MIGRATION-TO-MCPSTANDARD.md` |
| Project source | `~/projects/mcp/code-executor/` |
| Compose file | `~/projects/mcp/code-executor/docker-compose.yml` |
| Wrapper today (administrator) | `~administrator/.claude/skills/mcp-wrapper.sh` |
| Wrapper today (websurfinmurf) | `~websurfinmurf/.claude/skills/mcp-wrapper.sh` |
| Wrapper after (shared) | `/usr/local/bin/mcp-code-executor` |
| Dispatcher | `/usr/local/bin/mcp-dispatcher` |
| Key files (host) | `/home/administrator/projects/secrets/code-executor-{administrator,developer}.key` |
| Key files (in container) | `/run/secrets/code-executor-{administrator,developer}.key` |
| Roles map | `~/projects/mcp/code-executor/roles.json` (mounted at `/app/roles.json`) |
| Audit log | `journalctl -t mcp-dispatcher -t mcp-code-executor` |

Read `MCPSTANDARD.md` first, then this file. The standard has the *what*; this file has the *what-needs-to-change-on-this-particular-machine*.
