# Security

## Trust model
- [IMPLEMENTED] Tier-1: LAN/VPN only, no Keycloak, no public exposure. Trust boundary is host Linux group membership (`administrators` / `developers`).
- [IMPLEMENTED] Per-MCPSTANDARD §5: intra-role isolation is **zero by design**. Anyone in `administrators` group can read the admin keyfile and bypass the wrapper. Acceptable for 1–2 trusted users per role.

## Keyfile boundaries
- [IMPLEMENTED] Host: `/home/administrator/projects/secrets/code-executor-<role>.key`, mode `0640`, owner `root:<role-group>`.
- [IMPLEMENTED] Container: bind-mounted RO at `/run/secrets/`. Read access is enforced per-call by `docker exec --user 1000:<role-gid>`:
  - Admin exec: `--user 1000:2000` → can read admin keyfile, BLOCKED on developer keyfile.
  - Developer exec: `--user 1000:3000` → can read developer keyfile, BLOCKED on admin keyfile.
  - Default container UID `1000:1000` (executor.ts and any user-supplied code via `execute_code`) → BLOCKED on both keyfiles.
- [IMPLEMENTED] Key delivery via `MCP_KEY_FILE` (path), never raw bytes in argv/env. Defense against `/proc/<pid>/environ` and `ps auxe` leaks.

## Audit identity
- [IMPLEMENTED] `MCP_SENDER_NAME` stamped server-side from kernel-attested `id -un` + `SSH_CLIENT`. Format: `<user>@linuxserver-local` (server-local) or `<user>@<peer-IP>-via-ssh` (laptop).
- [IMPLEMENTED] Client-supplied `MCP_*` env scrubbed by dispatcher; wrapper does not trust caller-supplied identity.

## Audit logs
- [IMPLEMENTED] `journalctl -t mcp-code-executor` — one line per wrapper invocation: `user=... role=... sender=...`.
- [IMPLEMENTED] `journalctl -t mcp-dispatcher` — ACCEPT/REJECT lines for each laptop SSH attempt. Empty for server-local invocations (server-local bypasses dispatcher).
- [IMPLEMENTED] Container logs (json-file driver, 10MB × 3 rotation) — tool execution traces from `executor.ts`.
- **Note on `sender=user@<IP>-via-ssh`:** the IP is a *join key* into `/var/log/auth.log`, NOT the device-identity primitive. Stable device identity is the SSH key fingerprint, which sshd records on the same line as the IP+user (`sshd: Accepted publickey for ... from <IP> ... SHA256:<fp>`). To attribute a laptop across DHCP-lease changes, grep auth.log by user+timestamp, pull the fingerprint, then correlate against `~<user>/.ssh/authorized_keys` comments. Don't replace the wrapper IP with reverse-DNS hostname: hostnames are unauthenticated (PTR-spoofable on a compromised LAN) and add DNS latency to the cold-start §8.D3 budget. If self-contained audit lines ever become a hard requirement, enable `ExposeAuthInfo yes` in `sshd_config` and read `$SSH_AUTH_INFO_0` in the wrapper to embed the fingerprint directly. Decision recorded 2026-04-27.

## Laptop SSH access
- [IMPLEMENTED, when configured] `authorized_keys` lines MUST start with `restrict,command="/usr/local/bin/mcp-dispatcher",no-user-rc`. Without this, the laptop key grants full shell access. The negative test (`ssh -T <user>@linuxserver.lan ls /` → MUST be FATAL) catches regression.
- [IMPLEMENTED, when configured] Laptop uses dedicated keypair `~/.ssh/id_ed25519_mcp` (NOT general SSH key); `IdentitiesOnly=yes` + explicit `-i` prevents ssh-agent from offering an unrestricted key.

## Container hardening
- [IMPLEMENTED] `no-new-privileges:true`.
- [IMPLEMENTED] `read_only: false` (need `/tmp/executions` write for code exec sandbox); `/tmp/executions` mounted `noexec,nodev,nosuid`.
- [IMPLEMENTED] Resource limits: 1 CPU core, 1GB RAM, 5-min execution timeout, 100KB output cap.
- [IMPLEMENTED] Docker socket mounted RO. Group `127` (host docker GID) for `docker ps` / inspect access.
- [PLANNED] tmpfs uid/gid in compose (currently requires `chown -R node:node` post-deploy workaround).

## Explicit accepted limits
- Docker socket = effective host privilege. Anyone in `docker` group can `docker exec --user` any UID and bypass the wrapper. Platform-wide property.
- `roles.json` mounted RO from project dir. Whoever can write `/home/administrator/projects/mcp/code-executor/roles.json` (administrator user) can register new keys.
- Container image supply chain: image rebuild is implicit trust on the build path.
- `SSH_CLIENT` in `MCP_SENDER_NAME` is device-IP, not user-identity. Multiple devices behind one NAT collapse to the same value. Useful breadcrumb, not user audit.
