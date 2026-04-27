# MCP service standard for linuxserver.lan
**Status:** v3.1 PRODUCTION — code-executor reference implementation deployed and verified end-to-end (server-local + websurfinmurf laptop §8). Two §3c bugs caught during execution have been folded back into the standard.
**Authored by:** administrator-claude · 2026-04-26 (v3); updated 2026-04-27 (v3.1 post-execution fixes).
**Precedent:** `/mnt/shared/mcpfix.md` (websurfinmurf-claude's SSH-piped-stdio fix for code-executor).
**Review history:** Gemini v1 (integrated → v2). Codex v2 + Claude review-board v2 (integrated → v3, see §9). Code-executor migration 2026-04-27 (integrated → v3.1, see §10).

This document proposes the **canonical pattern for all Tier-1 MCP services** on this server. Tier-1 = internal admin/developer tooling (per `~/projects/CLAUDE.md` "Platform Architecture Intent"). Tier-2 (external-facing apps via Traefik+Keycloak) is out of scope.

---

## 1. Goal

A single, repeatable pattern for adding MCP services that:
- Works for both server-local Claude Code sessions AND laptop Claude Code sessions over LAN/VPN.
- Uses simple key-based auth (group-gated key files), matching the existing `mcp-code-executor` model.
- Adds zero new external-facing infrastructure (no nginx, no TLS, no public-CA bootstrap, no Keycloak claim mappers).
- Survives the operational realities of stdio-over-SSH: handshake timeouts, sshd restarts, MCP `initialize` deadlines, multiple MCPs from one device.

## 2. Reference architecture

```
Claude Code
  ├─ on the server: spawns /usr/local/bin/mcp-<name> directly (stdio child).
  └─ on a laptop:   spawns `ssh -T <user>@linuxserver.lan mcp <name>`.
                    SSH multiplexing (ControlMaster) keeps a persistent socket
                    so per-invocation handshake cost is ~20ms after the
                    first connection — well under MCP's initialize timeout.
                                  │
                                  ▼  (server side)
   /usr/local/bin/mcp-dispatcher   ← only entry point sshd allows for the laptop key
        │ reads SSH_ORIGINAL_COMMAND ("mcp <name>")
        │ validates <name> against an allow-list (literal names only)
        │ logs invocation to syslog
        │ exec /usr/local/bin/mcp-<name>
        ▼
   /usr/local/bin/mcp-<name>       ← shared wrapper, root-owned, mode 0755
        │ resolves role from kernel-attested group membership
        │ logs invocation to syslog
        │ mounts secrets/<mcp-name>-<role>.key into container as a file
        │ stamps MCP_SENDER_NAME server-side from real identity
        │ exec docker exec -i <mcp-name>-container <stdio entry-point>
        ▼
   <mcp-name> container (no published host ports)
        │ reads MCP_KEY_FILE (mounted), validates SHA-256 + constant-time vs keys.json
        │ runs MCP stdio server bound to the resolved role
        │ container env holds DSNs / backend creds
        ▼
   Backend services (TimescaleDB, MinIO, etc., on internal docker network)
```

## 3. Required components

### 3a. Server-side container
- Long-running (`restart: unless-stopped`); naming `mcp-<name>` (container) and `<name>` as the MCP logical name.
- On the docker network(s) needed for its backends.
- Backend creds in container env, mounted from `/home/administrator/projects/secrets/<mcp-name>.env` (mode 0600 root-owned).
- Mount the **secrets directory** read-only at `/run/secrets/` inside the container so keys are file-delivered, not env-delivered (see §3c). The keyfile lives on the host at `/home/administrator/projects/secrets/<mcp-name>-<role>.key` and is bind-mounted into the container's `/run/secrets/` — same bytes, two views; the host path never moves. `/run/secrets/` is the FHS-conventional in-container location for runtime-only secrets.
- Stdio MCP entry-point reads `MCP_KEY_FILE` (path inside container) at startup, validates with **SHA-256 + constant-time compare** against `keys.json` (root-owned in image, mounted read-only), refuses unknown keys.
- **Container UID hardening — required for any service that also runs untrusted user code.** Long-lived container processes (e.g. an HTTP API, a code-executor sandbox, anything that processes attacker-influenced input) MUST run with a UID/GID that **cannot read** `/run/secrets/<mcp-name>-*.key` directly. The keyfile read happens only inside the short-lived MCP exec subprocess via `docker exec --user "<container-uid>:<role-gid>"` (see §3c). Without this, `chmod 0644` or `group_add: ["<role-gid>"]`-style fixes leak every role's keyfile to user code running in the same container, defeating the role boundary entirely. For containers that contain *only* the MCP entry-point and no other process surface, the constraint is trivially met.
- Containers running Python: set `PYTHONUNBUFFERED=1` to avoid stdio buffering eating JSON-RPC. Equivalent flush guarantee for Node servers.
- **Does NOT publish any host ports.** Access exclusively via `docker exec`.
- **Symmetric to sshd-restart caveat (§6):** container restart kills all in-flight `docker exec` sessions and any in-flight tool call fails once. Self-heals on next invocation.

### 3b. Server-side key files
- Path: `/home/administrator/projects/secrets/<mcp-name>-<role>.key` (singular role: `administrator` | `developer`).
- Mode `0640`, owner `root:<role-group>` where role-group is the plural Linux group (`administrators` | `developers`). The keyfile name uses the **singular** role; the group uses the **plural**. Standardised: do not mix.
- Content: 256-bit random token, base64url, **exactly N bytes with NO trailing newline**.
  - Generate with: `openssl rand -base64 32 | tr -d '\n' > "$KEY_FILE" && chmod 0640 "$KEY_FILE"`.
  - Hash registration in `keys.json`: `sha256(file-bytes-as-bash-reads-them)`. Bash `KEY="$(<f)"` strips trailing newlines, so registration must hash the **trimmed** bytes. Generator above emits no trailing newline; both paths agree.
- One file per role; one role per tenant.
- **Per-user upgrade path (documented, not default).** At any future point this pattern flips trivially to per-user audit: rename to `<mcp-name>-<user>.key`, mode `0600` owned by `<user>:<user>`, wrapper resolves by `id -un`, container `keys.json` maps key-hash → user. No structural change. Default stays role-keyed because today's users-per-role is 1–2 and the role provides backend-cred boundary; flip when user count grows OR per-user audit becomes a requirement.

### 3c. Server-side wrapper at `/usr/local/bin/mcp-<name>`
- Root-owned, mode `0755`. Single shared wrapper per MCP — NOT per-user.
- Logic:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  IFS=$' \t\n'
  REAL_USER=$(id -un)

  # Group resolution — exact match, not substring. Checks BOTH primary group
  # (via id -gn) AND supplementary members. The primary-group check is the
  # critical one: users whose role IS their primary group typically have an
  # empty supplementary member list (e.g. `administrators:x:2000:` with no
  # 4th-field members), and a supplementary-only check would silently miss
  # them. grep -w also breaks on hyphenated group names ("super-administrators"
  # matches "administrators"); literal compare via awk avoids that bug.
  in_group() {
      [[ "$(id -gn "$REAL_USER")" == "$1" ]] && return 0
      local g
      while IFS= read -r g; do [[ "$g" == "$REAL_USER" ]] && return 0; done < <(
          getent group "$1" | awk -F: '{gsub(",","\n",$4); print $4}'
      )
      return 1
  }

  if in_group administrators; then
      ROLE=administrator
      ROLE_GID=$(getent group administrators | awk -F: '{print $3}')
  elif in_group developers; then
      ROLE=developer
      ROLE_GID=$(getent group developers | awk -F: '{print $3}')
  else
      echo "FATAL: $REAL_USER not in administrators or developers" >&2
      exit 2
  fi
  # NOTE: a user in BOTH groups resolves to administrator (admin wins). Stated
  # explicitly so this is not a surprise.

  KEY_FILE="/home/administrator/projects/secrets/<mcp-name>-${ROLE}.key"
  [[ -r "$KEY_FILE" ]] || { echo "FATAL: cannot read $KEY_FILE" >&2; exit 2; }

  # Audit identity stamped server-side from kernel-attested REAL_USER.
  # SSH_CLIENT, when present, is the immediate peer IP — useful as a
  # device-level breadcrumb but NOT a user identity (VPN/NAT collapses devices).
  if [[ -n "${SSH_CLIENT:-}" ]]; then
      MCP_SENDER_NAME="${REAL_USER}@${SSH_CLIENT%% *}-via-ssh"
  else
      MCP_SENDER_NAME="${REAL_USER}@$(hostname -s)-local"
  fi

  logger -t "mcp-<mcp-name>" "user=$REAL_USER role=$ROLE sender=$MCP_SENDER_NAME"

  # Key delivery: mount the keyfile into the container at a known path; pass
  # only the path via env. Avoids putting raw key bytes in argv/environ where
  # /proc readers (host root, ps auxe) could harvest them. The `--user
  # <container-uid>:${ROLE_GID}` override binds keyfile read access to THIS
  # exec subprocess only — long-lived container processes at the default UID
  # cannot read the role keyfiles, even though /run/secrets is mounted into
  # the same filesystem. This is what makes group_add / chmod 0644 unsafe and
  # what makes this pattern safe (see §3a "Container UID hardening").
  exec docker exec -i \
      --user "<container-uid>:${ROLE_GID}" \
      -e MCP_KEY_FILE="/run/secrets/<mcp-name>-${ROLE}.key" \
      -e MCP_SENDER_NAME="$MCP_SENDER_NAME" \
      -e MCP_ROLE="$ROLE" \
      mcp-<mcp-name> \
      <stdio entry-point command>
  ```
- The container's compose file mounts `/home/administrator/projects/secrets/` read-only at `/run/secrets/` so the keyfile is reachable via `MCP_KEY_FILE`. The keyfile NEVER leaves `/home/administrator/projects/secrets/` on the host — the bind mount surfaces the same bytes inside the container at the FHS-conventional `/run/secrets/` path. **Replace `<container-uid>` with the UID the container's image runs under** (e.g. `1000` for a container whose Dockerfile ends with `USER node`); the role-group GID is read from the host's group database at wrapper time, so the same wrapper logic works on any host without hardcoding numeric GIDs.
- No raw key in argv/env. Audit identity stamped from kernel-attested `id -un`, not client-supplied env.
- **Verify role-bound key access after install.** From the host: `docker exec --user "<container-uid>:<other-role-gid>" mcp-<mcp-name> head -c 8 /run/secrets/<mcp-name>-<role>.key` MUST return `Permission denied` for the wrong role. If it succeeds, the role boundary is broken (likely the wrong UID:GID combo, or the keyfile owner/mode drifted).

### 3d. Server-side dispatcher at `/usr/local/bin/mcp-dispatcher`
- New component, root-owned, mode `0755`. Single entry point invoked by every laptop SSH key.
- Logic:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  IFS=$' \t\n'

  # Defense in depth: scrub any MCP_* env the client may have shipped via
  # AcceptEnv. The wrapper re-sets what it needs from kernel-attested data.
  while IFS= read -r v; do unset "$v"; done < <(compgen -e | grep '^MCP_' || true)

  read -r cmd target extra <<< "${SSH_ORIGINAL_COMMAND:-}"
  if [[ "$cmd" != "mcp" || -z "$target" || -n "$extra" ]]; then
      logger -t mcp-dispatcher "REJECT user=$(id -un) cmd='${SSH_ORIGINAL_COMMAND:-}' client=${SSH_CLIENT%% *}"
      echo "FATAL: dispatcher expects exactly: 'mcp <name>'" >&2
      exit 2
  fi

  # Allow-list — LITERAL names only. case patterns are globs; do not introduce
  # wildcards here. Extend when adding a new MCP service.
  case "$target" in
      code-executor|agent-memory) ;;
      *)
          logger -t mcp-dispatcher "REJECT user=$(id -un) target='$target' client=${SSH_CLIENT%% *}"
          echo "FATAL: unknown MCP '$target'" >&2
          exit 2
          ;;
  esac

  logger -t mcp-dispatcher "ACCEPT user=$(id -un) target=$target client=${SSH_CLIENT%% *}"
  exec "/usr/local/bin/mcp-$target"
  ```
- Why a dispatcher: `authorized_keys` matches by **first occurrence of a pubkey** — multiple lines with the same pubkey + different `command="..."` cause silent failure of all but the first. One dispatcher line per laptop key; dispatcher routes by `SSH_ORIGINAL_COMMAND`.
- Both dispatcher and wrapper write a single-line `logger` audit record per invocation. Tail with `journalctl -t mcp-dispatcher -t mcp-<name>` for the full trail.

### 3e. Server-local Claude Code config (`~/.claude.json`)
```json
"<mcp-name>": {
  "type": "stdio",
  "command": "/usr/local/bin/mcp-<name>",
  "args": [],
  "env": {}
}
```

### 3f. Laptop Claude Code config (`~/.claude.json`)
```json
"<mcp-name>": {
  "type": "stdio",
  "command": "ssh",
  "args": [
    "-T",
    "-o", "BatchMode=yes",
    "-o", "IdentitiesOnly=yes",
    "-i", "~/.ssh/id_ed25519_mcp",
    "<user>@linuxserver.lan",
    "mcp <mcp-name>"
  ],
  "env": {}
}
```
- `-T` disables PTY allocation (avoids docker exec stdin/stdout buffering surprises).
- `BatchMode=yes` fails fast on unknown host key or missing pubkey rather than blocking on a prompt.
- `IdentitiesOnly=yes` + explicit `-i` prevents ssh-agent from offering some other key (which might NOT be dispatcher-restricted and would grant a shell).
- Recommend a **dedicated keypair for MCP** (`id_ed25519_mcp`), not the user's general SSH key — keeps dispatcher restriction tight and rotation independent.
- `MCP_SENDER_NAME` is **NOT** set client-side — server-side wrapper stamps the real identity (§3c).

### 3g. Laptop SSH multiplexing (mandatory)
**MCP `initialize` has a strict ~2-3s timeout. A cold SSH handshake over VPN can blow that.** Mitigation: persistent control socket so the handshake cost is paid ONCE per device per session.

In `~/.ssh/config` on the laptop:
```
Host linuxserver.lan
    User <user>
    IdentitiesOnly yes
    IdentityFile ~/.ssh/id_ed25519_mcp
    ControlMaster auto
    ControlPath ~/.ssh/cm-%h-%p-%r
    ControlPersist 1h
    ServerAliveInterval 60
    ServerAliveCountMax 3
```
- `ControlPath ~/.ssh/cm-%h-%p-%r` — short tokens (~30 chars). Avoid `%C` (64-char SHA-256 hex), which combined with a long `$HOME` overruns the 108-byte Linux / 104-byte macOS Unix-socket path limit and silently disables multiplexing.
- **`~/.ssh/` MUST be on a local filesystem.** Unix-domain sockets do not work on NFS; multiplexing silently degrades to per-call full handshakes if `~/.ssh/` is NFS-mounted (corp roaming profiles do this). If unavoidable, set `ControlPath /tmp/cm-%h-%p-%r` (assuming `/tmp` is local tmpfs) instead.
- `ControlPersist 1h` — long enough that "close lid → lunch → reopen" still hits the warm socket. `10m` was too short for realistic laptop work-rhythm.
- `ServerAliveInterval 60` + `ServerAliveCountMax 3` — keeps long-lived MCP sessions from dropping over idle VPN links.
- **Master-crash blast radius:** the multiplexed master is a single failure surface. Network blip, sshd-side restart, OOM → ALL slaves die simultaneously across all concurrent Claude Code instances on that laptop. The next invocation re-creates the master, but every in-flight tool call fails at once. Acceptable; flagged so it isn't a surprise.
- **`MaxSessions 10` ceiling.** Default sshd allows 10 concurrent channels per multiplexed connection. Heavy parallel tool-call workloads can hit this. Either raise on the server (`/etc/ssh/sshd_config`: `MaxSessions 30`) or accept the ceiling.

Without multiplexing, every `claude mcp list` and every tool call pays the full handshake cost, which often exceeds MCP's initialize timeout.

### 3h. Server-side SSH access (one-time per laptop)
The laptop's pubkey goes in `/home/<user>/.ssh/authorized_keys` with a **mandatory** dispatcher restriction:

```
restrict,command="/usr/local/bin/mcp-dispatcher",no-user-rc ssh-ed25519 AAAA... <user>@<device>-mcp
```

- `restrict` is the OpenSSH umbrella option that disables PTY, port-forwarding, X11 forwarding, agent forwarding, and tunneling in one token. Future-proof against new forwarding features.
- `no-user-rc` blocks `~/.ssh/rc` execution (a separate code-execution path that `restrict` does not cover).
- `command="..."` forces every connection through the dispatcher regardless of `SSH_ORIGINAL_COMMAND`.

**Without `restrict,command="..."` the laptop key grants full shell access.** The standard makes it mandatory; ops automation MUST enforce — `grep ^command= authorized_keys` should match every MCP key entry.

Adding more MCPs later does NOT require new `authorized_keys` lines — the dispatcher routes by `SSH_ORIGINAL_COMMAND`. Just add the new MCP to the dispatcher's allow-list (§3d) and ship a new `<mcp-name>` wrapper + container.

### 3i. Server-side `known_hosts` for the laptop (one-time)
Before first `BatchMode=yes` connection from the laptop:
```bash
# From a trusted point (NOT the path that would be MITM'd):
ssh-keyscan -H linuxserver.lan >> ~/.ssh/known_hosts
```
or use `StrictHostKeyChecking=accept-new` in the laptop SSH config for first contact. `BatchMode=yes` fails immediately if the host key is unknown — must be present before the first MCP invocation.

### 3j. Operator runbooks

**Key rotation (per-role keyfile):**
1. Generate new key: `openssl rand -base64 32 | tr -d '\n' > /tmp/newkey`.
2. Compute hash: `sha256sum /tmp/newkey`.
3. Append the new hash to the container's `keys.json` mapped to the same role; rebuild the image OR redeploy with a mounted `keys.json` from `secrets/`.
4. `mv /tmp/newkey /home/administrator/projects/secrets/<mcp-name>-<role>.key && chmod 0640 && chown root:<role-group>`.
5. Restart the container (`docker compose restart mcp-<name>`). In-flight sessions fail once; clients reconnect transparently.
6. After all clients have reconnected (next session), remove the old hash from `keys.json` and redeploy.

Recommendation: mount `keys.json` from `secrets/` rather than baking it into the image — decouples rotation from rebuild.

**Key revocation (lost laptop):**
1. `sed -i '/comment-of-laptop-key/d' /home/<user>/.ssh/authorized_keys` — kills the SSH leg.
2. Optionally rotate the role keyfile per the procedure above if the laptop also had non-MCP access to it.
3. `journalctl -t mcp-dispatcher --since '7 days ago' | grep <client-IP-of-laptop>` to audit prior usage.

## 4. Adding a new MCP — checklist

1. Build container `mcp-<name>`; no host ports published; mount `secrets/` at `/run/secrets/` read-only; `keys.json` validated SHA-256 + constant-time; `PYTHONUNBUFFERED=1` (or equivalent) set.
2. Provision per-role keys at `/home/administrator/projects/secrets/<mcp-name>-<role>.key`, mode 0640, **no trailing newline**.
3. Container reads `MCP_KEY_FILE` at startup; refuses unknown keys.
4. Install `/usr/local/bin/mcp-<name>` per §3c (root-owned, 0755).
5. Add `<name>` to `mcp-dispatcher`'s allow-list (§3d).
6. Add server-side `~/.claude.json` block per §3e for users who use it server-local.
7. For each laptop that needs access:
   - Add `~/.claude.json` block per §3f.
   - Confirm laptop `~/.ssh/config` has the multiplexing block (§3g) — usually already there from prior MCP onboarding.
   - Confirm laptop's pubkey is already in server's `authorized_keys` with `restrict,command="..."` — usually already there from prior MCP onboarding.
   - One-time: `ssh-keyscan` to populate `known_hosts` if first contact.
8. Smoke test:
   - **Server (positive):** spawn `/usr/local/bin/mcp-<name>` directly, pipe an `initialize` request on stdin, expect a response.
   - **Laptop (positive):** `ssh -T -o BatchMode=yes <user>@linuxserver.lan "mcp <mcp-name>"` opens; pipe an `initialize` request on stdin and confirm response. (`ssh ... true` will be REJECTED by the dispatcher — that is correct, not a failure.)
   - **Laptop (negative):** `ssh -T <user>@linuxserver.lan ls /` MUST be rejected with the dispatcher's "FATAL" message. If a shell prompt or directory listing appears instead, the `restrict,command="..."` line is missing or malformed — STOP and fix before exposing more MCPs.
   - **Laptop (cold-start):** sleep > `ControlPersist`, then `claude mcp list` — confirm a fresh master is built within MCP's initialize timeout.
   - **Laptop (master proof):** `ls -l ~/.ssh/cm-*` after first call — should show a Unix socket. If empty, multiplexing is silently disabled (likely NFS or path-length).

## 5. Trust model (explicit)

| Boundary | Enforced by |
|---|---|
| Tenant separation (admin vs developer) | Group-gated key file perms + container key→role lookup + role-bound DB credentials in container env |
| Backend credentials never on host (other than `/home/administrator/projects/secrets/`) | Container env; `secrets/` only readable by root + the matching role group |
| Laptop access scoped to MCP only | `restrict,command="/usr/local/bin/mcp-dispatcher",no-user-rc` on `authorized_keys` (mandatory) + dispatcher allow-list (literal names) + dispatcher MCP_* env scrub |
| Audit identity (`MCP_SENDER_NAME`) | Stamped server-side from kernel-attested `id -un` + `SSH_CLIENT`. Client cannot forge. |
| Key bytes off argv/environ | Wrapper passes `MCP_KEY_FILE` (path), not the key. Container reads file in its own process space. |
| No external network exposure | Container does not publish ports; SSH is the only inbound transport from off-host |

**Explicit limits (intra-tier, by design):**

- **Intra-role isolation is zero.** Group-readable key file means any process running as a user in the role-group can read the raw key and bypass the wrapper (e.g. `docker exec` directly with `MCP_ROLE` set). Fine for 1–2 trusted users in the same role; NOT a defense against a malicious teammate within the same role. Per-user upgrade path documented in §3b.
- **Docker socket = effective privilege.** Anyone in the `docker` group can `docker exec` into any container and bypass the wrapper entirely. Platform-wide property accepted on this server.
- **No per-user audit at the MCP layer (today).** `MCP_SENDER_NAME` carries device-level distinction but auth resolves to a role, not a user. Per-user audit is a §3b config flip away.
- **`SSH_CLIENT` is device-IP, not user-identity.** On VPN this is the WireGuard endpoint — useful as a breadcrumb, but multiple devices behind one NAT collapse to the same value. Don't over-claim it as user-level audit.
- **Process-environ key visibility (host root only).** Even with `MCP_KEY_FILE` (path-not-bytes), host-root can `cat` the keyfile. This is intrinsic to running on a shared host; only role-separation defends against it. Acceptable at this trust tier.
- **Container image supply chain.** `keys.json` lives in the image (or mounted from `secrets/`); whoever can rebuild/republish (CI, image registry, or root) can replace registered hashes. Implicit trust on the image build path.
- **`restrict,command="..."` is the ONLY thing keeping a laptop key from full shell access.** If ever omitted on a future entry, that laptop has full access. Standard makes it mandatory; the §4 negative smoke test catches regression.

## 6. Tradeoffs accepted

- **SSH session lifecycle = MCP session lifecycle.** sshd restart drops in-flight MCP sessions. Self-heals on next invocation; in-flight tool call fails once. Acceptable.
- **Container restart symmetric with sshd restart.** `docker compose restart mcp-<name>` kills in-flight `docker exec` sessions; same self-heal behaviour as sshd-restart. Plan key rotations and image updates accordingly.
- **Multiplexed master is a single failure surface.** Master crash drops all concurrent MCP slaves on that laptop simultaneously. Acceptable for 1–2 concurrent Claude Code instances; revisit if parallelism grows.
- **Zombie process risk.** If Claude Code crashes without sending clean EOF, both the laptop's `ssh` process and the server's `docker exec` may hang briefly until SSH keepalive detects the dead client (~3 minutes worst case at default settings).
- **`StrictHostKeyChecking=accept-new`** is fine for first contact in a controlled-setup workflow but means a MITM at first contact would pin the wrong host key. Pre-population via `ssh-keyscan` from a trusted point is preferred.

## 7. When to escalate to Tier 2 (Traefik + Keycloak)

Any of these conditions push the service out of this standard:
- Externally-reachable from the public internet.
- Used by end users (humans logging in via browser).
- Per-user identity required for compliance / audit AND user count > 5 OR organizationally-separate tenants.
- Multi-tenant with tenants that are organizationally separate (not "members of one team").

In those cases, use the platform's Tier-2 pattern (see `~/projects/CLAUDE.md`). Note: per-user audit alone does NOT force Tier-2 — it can be served by the §3b per-user-keys flip while remaining Tier-1.

## 8. Per-device verification questions for websurfinmurf-claude (laptop session)

Asked from the server side; answered from the laptop. Facts the server cannot directly observe.

1. Does `~/.ssh/config` have a `Host linuxserver.lan` block with `ControlMaster auto`, `ControlPath ~/.ssh/cm-%h-%p-%r` (or `/tmp/cm-...` if home is NFS), `ControlPersist 1h`, `ServerAliveInterval 60`, `IdentitiesOnly yes`, `IdentityFile ~/.ssh/id_ed25519_mcp`?
2. Is `~/.ssh/` on a **local** filesystem (not NFS / not roaming-profile-synced)? If NFS, multiplexing silently fails.
3. Is the server's host key in `~/.ssh/known_hosts` (or are you OK with `accept-new` on first contact)?
4. **Positive test:** does `ssh -T -o BatchMode=yes <user>@linuxserver.lan "mcp code-executor"` open a stdio session that responds to `initialize`?
5. **Negative test:** does `ssh -T <user>@linuxserver.lan ls /` produce the dispatcher's "FATAL" reject (NOT a directory listing or shell prompt)? This is the test that catches a missing `restrict,command="..."`.
6. **Cold-start test:** wait > `ControlPersist`, then `claude mcp list` — does it succeed within MCP's initialize timeout, or does the cold handshake blow it?
7. **Master-socket proof:** after first successful call, does `ls -l ~/.ssh/cm-*` show a Unix socket? Empty = multiplexing silently disabled.
8. **Key offered:** `ssh -v <user>@linuxserver.lan "mcp code-executor" 2>&1 | grep 'Offering\|Authenticated'` — confirm the dispatcher-restricted key is the one that authenticates, not some other key in `~/.ssh/` or ssh-agent.
9. After the first MCP onboarding via this standard, does adding a second MCP work entirely client-side (no `authorized_keys` change required), or is something missing on the dispatcher side?

## 9. Changes from v2 (Codex + Claude review-board round)

**Must-fix integrated:**
- §3b: key file canonicalization rule — no trailing newline, generator command pinned, hash registration matches bash-read bytes (Codex MEDIUM, Claude MUST).
- §3c: replaced `id -Gn | grep -qw` with `getent group` + literal compare. Eliminates whole-word-match bug on hyphenated group names like `super-administrators` (Claude MUST bug catch).
- §3c: key delivery via mounted file path (`MCP_KEY_FILE`) instead of `-e MCP_API_KEY="$KEY"` argv — keeps raw key off `/proc/<pid>/environ` and `ps auxe` output (Codex HIGH).
- §3c, §3d: both wrapper and dispatcher write `logger -t` audit lines — no more silent gatekeeper (Claude MUST).
- §3d: `IFS=$' \t\n'` pinned, `MCP_*` env scrubbed defensively, "literal names only — no globs" comment (Codex MEDIUM, Claude SHOULD).
- §3g: `ControlPersist` raised 10m → 1h to survive laptop work-rhythm (Claude MUST).
- §3g: `ControlPath` switched from `%C` to `%h-%p-%r` to stay under the 108-byte Unix-socket path limit; NFS-home warning added (Claude MUST).
- §3h: `restrict,command="...",no-user-rc` replaces enumerated `no-pty,no-port-forwarding,...` — future-proof and covers `~/.ssh/rc` (Codex MEDIUM).
- §4 step 8: smoke-test fixed — `ssh ... true` is REJECTED by the dispatcher; positive test is `ssh ... "mcp <name>"` with a real `initialize` payload (Codex HIGH, Claude MUST).
- §4: negative test (`ssh ... ls /` MUST reject), cold-start test, master-socket-presence test added (Claude SHOULD).

**Should-fix integrated:**
- §3b: per-user-keys upgrade path documented as the natural next step (Claude SHOULD — pushed back on per-user-as-default; documented as flip rather than redefault, since today's user count is 1–2).
- §3j: key rotation runbook + revocation runbook added (Claude SHOULD).
- §3g: `MaxSessions 10` ceiling, master-crash blast-radius, race-on-first-connect notes (Claude WORTH-ONE-LINE).
- §3a: container restart symmetric with sshd restart (Claude WORTH-ONE-LINE).
- §3c: explicit "admin wins if user is in both groups" note (Claude WORTH-ONE-LINE).
- §3f: dedicated MCP keypair (`id_ed25519_mcp`) recommended; explicit `IdentityFile` defends against ssh-agent offering an unrestricted key.
- §5: process-environ leakage (host-root visibility), `SSH_CLIENT` as device-not-user, container image supply chain — all stated explicitly.
- §7: per-user audit alone does NOT force Tier-2 — the §3b flip serves it within Tier-1.

**Reviewer recommendations NOT adopted (with reasoning):**
- Per-user keys as default. Claude review-board recommended this; deferred. At today's 1–2 users-per-role, role keys are operationally simpler and the upgrade path is one config change. Will reconsider when user count crosses 3 or when per-user audit becomes a concrete requirement.
- Multi-server dispatcher abstraction. Claude review-board flagged this for >12-month horizon; YAGNI for now, the per-host pattern is fine.
- `mcp-exec` helper to abstract `docker exec` away from the wrapper. Claude review-board's container-runtime-portability note; YAGNI — `docker exec` is the one supported runtime here.

## 10. Changes from v3 (post-execution lessons from code-executor migration, 2026-04-27)

Two real bugs surfaced when `code-executor` became the v3 reference implementation. Both are fixes to concrete failure modes observed in the running migration, not redesigns. Anyone reading the standard before this section should re-read §3a and §3c.

**Must-fix integrated:**
- §3c `in_group()` now also checks the user's PRIMARY group via `id -gn`. The supplementary-only check silently misses any user whose role IS their primary group with an empty supplementary list (e.g. an `administrator` user with `administrators` as primary GID and no supplementary members — `getent group administrators` returns `administrators:x:2000:`). On the linuxserver.lan reference host, this is the default user setup, so the previous standard's wrapper FATALed on legitimate calls.
- §3c `docker exec` now MUST include `--user "<container-uid>:${ROLE_GID}"`. Without it, the container UID either can't read `/run/secrets/<role>.key` (mode 0640 root:role-group) at all, OR — if "fixed" with `chmod 0644` or `group_add` — leaks every role's keyfile to long-lived processes and any user-supplied code in the same container, defeating the role boundary entirely. The `--user` override binds keyfile read access to the short-lived MCP exec subprocess only.
- §3a now states the container UID hardening requirement explicitly: long-lived processes that handle attacker-influenced input MUST run with a UID/GID that cannot read `/run/secrets/<role>.key`. The `--user` override is what implements this; standard now says so up-front rather than leaving it to be re-derived.
- §3a now clarifies that `/run/secrets/` is the IN-CONTAINER mount path, not a host path — keyfiles never leave `~/projects/secrets/` on the host. (Previous wording could be misread as relocating the canonical home.)

**Should-fix integrated:**
- §3c wrapper now derives `ROLE_GID` dynamically from `getent group <role-group>` rather than hardcoding numeric GIDs, so the standard works on hosts where `administrators`/`developers` aren't 2000/3000.
- §3c adds a post-install verification step: `docker exec --user "<container-uid>:<other-role-gid>"` reading the wrong role's keyfile MUST return `Permission denied`. Catches role-boundary regressions caused by drifted file ownership/mode.

**Source:** code-executor `MIGRATION-TO-MCPSTANDARD.md §10` records the empirical evidence behind each fix (verified by `docker exec --user 1000:2000` reads admin key but is blocked on developer key; `docker exec --user 1000:1000` is blocked on both).

---

*v3.1 — code-executor is the production reference implementation. agent-memory v3 R1 adopts the same wrapper/dispatcher/keyfile pattern and inherits the §3a/§3c fixes from this section.*
