---
id: 2026-04-27-code-executor-tier1-b026c9
status: reserved
child_session_id: b026c92a-3cb0-490d-8e1a-5fc153c37100
spawn_mode: manual
spawned_at: 2026-04-27T10:03:42Z
launched_at: null
completed_at: null
source_dir: /home/administrator/projects/mcp
source_session_id: 3e133d69-4dc2-4ccb-a68a-434e837d74db
dest_dir: /home/administrator/projects/mcp/code-executor
slug: code-executor-tier1
parent_refocus_id: null
related_refocus_ids: []
done_when:
  - "All five MCPSTANDARD §8 verification tests pass for both administrator and websurfinmurf, from server-local AND laptop Claude Code sessions"
  - "mcp__code-executor__chat_who returns the correct Linux identity for both users"
  - "Per-user wrappers (~/.claude/skills/mcp-wrapper.sh) renamed .deprecated.<YYYY-MM-DD> for both users (not deleted)"
  - "Master index (~/projects/CLAUDE.md) names code-executor as the Tier-1 MCP reference implementation"
out_of_scope:
  - "agent-memory v3 R1–R6 work (separate thread at ~/projects/agents/memory/)"
  - "Designing or changing MCPSTANDARD itself — execute, don't relitigate"
  - "Any Keycloak/Traefik/OAuth integration — this is Tier-1 by design (LAN/VPN only)"
  - "Deleting (vs deprecating) per-user wrappers — leave for ~1 week minimum"
related: []
---

# Brief: Code-executor Tier-1 MCP migration (give websurfinmurf access)

## Why this branch exists
Developer `websurfinmurf` needs to use `mcp-code-executor` from his Claude Code session. Today only `administrator` has it wired — via per-user wrapper scripts and a `nogroup`-owned developer keyfile (broken). The Tier-1 MCP standard exists to fix exactly this pattern, and code-executor is its reference implementation — it must migrate to MCPSTANDARD before any other MCP server follows.

## Inherited context
- Source of truth for steps: `~/projects/mcp/code-executor/MIGRATION-TO-MCPSTANDARD.md` (steps 1–9). Execute, don't re-design.
- Standard reference: `~/projects/mcp/MCPSTANDARD.md` — §3 implementation, §8 verification.
- v3 design is final and reviewer-endorsed: dual-transport (Unix socket peer-cred + HTTPS TLS day-one). Do not relitigate.
- Host wrapper already rewritten to socat-relay variant (P2.1–P2.3 done). Migration doc reflects current state.
- Status verified 2026-04-26 (parent session). Remaining work:
  - **Step 1:** keyfile fixes — `code-executor-developer.key` is `root:nogroup`, must be `root:developers`; rename `code-executor-admin.key` → `code-executor-administrator.key` with backwards-compat symlink.
  - **Step 2:** container `MCP_KEY_FILE` support — edit `mcp-server.ts` + `docker-compose.yml`, rebuild, smoke-test.
  - **Steps 3–4:** install `/usr/local/bin/mcp-code-executor` and `/usr/local/bin/mcp-dispatcher` per MCPSTANDARD §3c–§3d (neither exists yet).
  - **Step 5:** switch `~administrator/.claude.json` and `~websurfinmurf/.claude.json` to the dispatcher path; restart Claude Code in each; verify `chat_who` works for both. (Unfinished P2.4.)
  - **Step 6:** deprecate per-user wrappers — rename `.deprecated.<date>`, do NOT delete for ~1 week.
  - **Step 7 (conditional):** drop host port `9091:3000` only after migration doc §3 confirms no external consumers.
  - **Step 8:** laptop side — SSH multiplexing + restricted-command authorized_keys + `~/.claude.json` block on each laptop. Five §8 verification tests.
  - **Step 9:** docs — update `~/projects/mcp/code-executor/CLAUDE.md` to point at MCPSTANDARD.md; add entry to `~/projects/CLAUDE.md` master index.
- Tier-1 service per `~/projects/CLAUDE.md` (LAN/VPN only, no Keycloak/Traefik). Don't drift to Tier-2.
- Audit log convention: `journalctl -t mcp-code-executor` records calling Linux identity per call.
- Engagement style: defend reviewer-validated v3/MCPSTANDARD decisions when probed; don't capitulate to Socratic questions.

## Open questions / desired deliverables
- All 9 migration steps executed against the live system in order.
- Step 1 verified with `ls -l` on both keyfiles.
- Step 5 `mcp__code-executor__chat_who` works for both users from server-local Claude Code.
- Step 8 five-test block passes for both users from server *and* laptop.
- Step 9 docs landed in both `~/projects/mcp/code-executor/CLAUDE.md` and `~/projects/CLAUDE.md`.
- Per-user wrappers renamed (not deleted).

## Hard rule for child
- Children are leaves. If you discover work that belongs in a different
  directory, do NOT call /refocus. Surface it in Result.suggested_follow_ups
  for the parent to decide.

## Pointer back
- Source session: `~/.claude/projects/-home-administrator-projects-mcp/3e133d69-4dc2-4ccb-a68a-434e837d74db.jsonl`
- To continue this child later: `cd /home/administrator/projects/mcp/code-executor && claude --resume b026c92a-3cb0-490d-8e1a-5fc153c37100`

---

## Result

### Status
- blocked — server-side migration complete and smoke-tested; final two acceptance criteria (server-local `chat_who` verification on both users, full §8 verification from each laptop) need work outside this session: a Claude Code restart in each user's server-local session, and laptop-side configuration on each laptop. A leaf-bound server session cannot do either.

### Definition-of-Done met
- [x] Per-user wrappers `~/.claude/skills/mcp-wrapper.sh` renamed `.deprecated.2026-04-27` for both administrator and websurfinmurf (not deleted).
- [x] Master index `~/projects/CLAUDE.md` names code-executor as the Tier-1 MCP reference implementation, pointing at `MCPSTANDARD.md`.
- [ ] `mcp__code-executor__chat_who` returns the correct Linux identity for both users — UNVERIFIED. Server-side wrapper produces correct `MCP_SENDER_NAME` (smoke-tested by piping `initialize` through `/usr/local/bin/mcp-code-executor` as administrator). Verification requires `/exit` + re-launch in each user's Claude Code session.
- [ ] All five §8 tests pass for both users from server-local AND laptop — UNVERIFIED for laptop. §8 tests 1, 2, 3, 4, 5 are SSH-specific and only run from a laptop client. Server-local does not use SSH (spawns wrapper directly). Laptop work was explicitly enumerated in the brief as the §8 portion of Step 8.

### Summary
Executed Steps 1–7 and 9 of `MIGRATION-TO-MCPSTANDARD.md` against the live system. Renamed and re-chowned both keyfiles to root:`<role-group>` with a backwards-compat symlink at `code-executor-admin.key`. Patched `mcp-server.ts` to read `MCP_KEY_FILE` (file-path) in addition to the legacy `CODE_EXECUTOR_API_KEY` env var, so raw key bytes never appear in `/proc/<pid>/environ`. Mounted `/home/administrator/projects/secrets` RO at `/run/secrets/` in the container. Installed `/usr/local/bin/mcp-dispatcher` (allow-list = `code-executor`) and `/usr/local/bin/mcp-code-executor` (group-resolved role + audit log + `MCP_KEY_FILE`). Updated both `~/.claude.json` files to point at the shared wrapper. Renamed both per-user wrappers to `.deprecated.2026-04-27` (kept; will delete in ≥ 1 week). Dropped the `9091:3000` host port publish after verifying no live consumers. Updated `code-executor/CLAUDE.md` and `projects/CLAUDE.md` to make code-executor the Tier-1 reference implementation.

Two real bugs surfaced and were fixed during smoke-testing — both deviate from vanilla MCPSTANDARD §3c and should be promoted back into the standard (see Section 10 of `MIGRATION-TO-MCPSTANDARD.md` for the record):

1. **`in_group()` only checked supplementary group members**, missing administrator (who has `administrators` as primary group with empty 4th field). Wrapper now also checks `id -gn`.
2. **`/run/secrets` mount + UID 1000 read access requires care**. The migration doc's `chmod 0644` / `group_add` suggestions both leak both keys to user-supplied code in `execute_code`. Solution: `docker exec --user "1000:${ROLE_GID}"` so the short-lived MCP exec subprocess (admin: 1000:2000, developer: 1000:3000) can read its role's keyfile only; the long-lived `executor.ts` (1000:1000) and any user code spawned via `execute_code` can read neither. Verified empirically.

Smoke tests run successfully:
- Positive: `cat init-rpc.json | /usr/local/bin/mcp-code-executor` → valid `initialize` response.
- Positive: `SSH_ORIGINAL_COMMAND="mcp code-executor" /usr/local/bin/mcp-dispatcher < init-rpc.json` → valid `initialize` response.
- Negative: `SSH_ORIGINAL_COMMAND="ls /" /usr/local/bin/mcp-dispatcher` → FATAL.
- Negative: `SSH_ORIGINAL_COMMAND="mcp evil-server" /usr/local/bin/mcp-dispatcher` → FATAL.
- Role-bound key access: 1000:2000 reads admin key only; 1000:3000 reads developer key only; 1000:1000 reads neither.

### Artifacts produced
- `mcp-server.ts` — added `loadApiKey()` reading `MCP_KEY_FILE`.
- `docker-compose.yml` — mounted `/run/secrets` RO; removed `9091:3000` publish.
- `/usr/local/bin/mcp-dispatcher` — root-owned 0755; allow-list = `code-executor`.
- `/usr/local/bin/mcp-code-executor` — root-owned 0755; primary-group fix + `--user 1000:<role-gid>` deviation.
- `/home/administrator/projects/secrets/code-executor-administrator.key` — renamed from `-admin.key`; symlink kept for compat.
- `/home/administrator/projects/secrets/code-executor-developer.key` — re-chowned `root:developers` (was `root:nogroup`).
- `~administrator/.claude.json` and `~websurfinmurf/.claude.json` — `code-executor.command` → `/usr/local/bin/mcp-code-executor`.
- `~administrator/.claude/skills/mcp-wrapper.sh.deprecated.2026-04-27` and websurfinmurf equivalent — preserved old wrappers.
- `MIGRATION-TO-MCPSTANDARD.md` Section 10 — completion record + deviations.
- `code-executor/CLAUDE.md` header + Architecture Role section — points at MCPSTANDARD.
- `projects/CLAUDE.md` Tier-1 paragraph — names code-executor as reference impl.
- Backups: `/tmp/codex-keys-backup-1777287956/` (key files + websurfinmurf .claude.json).

### Suggested follow-ups (parent decides)
- `~/projects/mcp/` — **promote both `MCPSTANDARD §3c` deviations back into the standard.** (a) `in_group()` should also check primary group via `id -gn` — the supplementary-only check silently fails for users whose role is their primary group. (b) `/run/secrets` mount is unsafe by default when the container also runs user-supplied code as the same UID; standard should prescribe `docker exec --user "<uid>:<role-gid>"` so the keyfile is readable only by the short-lived MCP exec subprocess, not by the long-lived process or its children. Slug: `mcpstandard-v3-fixes`.
- **Laptop side of Step 8 (websurfinmurf laptop, possibly administrator laptop too)** — generate `id_ed25519_mcp`, add multiplexing block per §3g, send pubkey to be appended with `restrict,command="/usr/local/bin/mcp-dispatcher",no-user-rc`, run all five §8 tests. This needs a Claude Code session ON THE LAPTOP, not on the server. Slug: `code-executor-laptop-tier1`.
- **Server-local `chat_who` verification on both users** — needs `/exit` + re-launch in each user's Claude Code session, then call `mcp__code-executor__chat_who`; expect `administrator@linuxserver-local` and `websurfinmurf@linuxserver-local`. Trivial; just needs a restart cycle the parent can ask the user to do.
- After 1 week of stable operation, **delete the `.deprecated.2026-04-27` wrapper files and the `code-executor-admin.key` backwards-compat symlink** (callers that read the old name will keep working until then; once nothing logs against them, remove).
- `~/projects/agents/memory/` — **agent-memory v3 build can now adopt the same wrapper/dispatcher/keyfile pattern from R1.** Add `agent-memory` to dispatcher's allow-list, add `~/projects/secrets/agent-memory-{administrator,developer}.key` with the same canonical generator, install `/usr/local/bin/mcp-agent-memory`, add `~/.claude.json` blocks. ~30 minutes per the §7 estimate. Slug already known: `agent-memory-v3-r1`.

### Material changes (for /context-save)
- `architecture` — Tier-1 MCP transport contract is now standardized on `MCPSTANDARD.md`; code-executor is the reference implementation. Wrapper at `/usr/local/bin/mcp-code-executor`, dispatcher at `/usr/local/bin/mcp-dispatcher`, file-delivered keys via `MCP_KEY_FILE=/run/secrets/code-executor-<role>.key`.
- `interfaces` — `mcp-server.ts` now reads `MCP_KEY_FILE` (path) preferentially over `CODE_EXECUTOR_API_KEY` (raw bytes). Container exposes no host ports; access only via `docker exec` or container-network DNS (`mcp-code-executor:3000`).
- `security` — keyfiles now `0640 root:<role-group>` with role-bound read enforced by `docker exec --user 1000:<role-gid>`; long-lived `executor.ts` and user code spawned via `execute_code` cannot read either keyfile. Audit identity stamped server-side from kernel-attested `id -un` (no client-supplied env trusted). Dispatcher writes `logger -t mcp-dispatcher`, wrapper writes `logger -t mcp-code-executor`.
- `gotchas` — `MCPSTANDARD §3c in_group()` doesn't check primary group, fails for users whose role is primary; vanilla `/run/secrets` recipe leaks both keys to user-supplied code. Both have local fixes documented in `MIGRATION-TO-MCPSTANDARD.md §10`.

### Child session
- Session jsonl: `~/.claude/projects/-home-administrator-projects-mcp-code-executor/b026c92a-3cb0-490d-8e1a-5fc153c37100.jsonl`
- Completed at: 2026-04-27T07:45:00Z (approximately)

<!--
When the child completes, /refocus-complete appends here:

### Status
- completed       # met all done_when criteria
- blocked         # hit a blocker requiring work in another directory; parent must orchestrate

### Definition-of-Done met
<checklist matching done_when from frontmatter, each item checked or noted as not met>

### Summary
<one paragraph: what was accomplished or where it blocked>

### Artifacts produced
- `<path>` — `<one-line description>`

### Suggested follow-ups (parent decides)
<bullets of "I noticed work belongs at <dir>" items the child surfaced for
parent to orchestrate. Each entry: dir, slug, one-line reason.>

### Material changes (for /context-save)
<list of decisions, contracts, or architecture changes that should be
promoted into <dest>/docs/context/* as canonical state. Each entry: which
context file (architecture | interfaces | conventions | gotchas | …) and
the one-line summary. Or: "N/A — investigation only, no canonical state
changed." Mandatory; child must enumerate explicitly before status flips.>

### Child session
- Session jsonl: `~/.claude/projects/-home-administrator-projects-mcp-code-executor/b026c92a-3cb0-490d-8e1a-5fc153c37100.jsonl`
- Completed at: <ISO ts>
-->
