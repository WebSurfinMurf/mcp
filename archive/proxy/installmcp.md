# Adding MCP Services to the Central Proxy

This runbook covers the recommended workflow for wiring additional MCP services into the central proxy running on `http://linuxserver.lan:9090`. Follow these steps whenever you introduce a new backend (native SSE server or stdio bridge) so it becomes available to Claude Code and other MCP clients via the proxy.

---

## 1. Prepare the Service Container
1. **Create a dedicated project directory** under `projects/mcp/<service>` following the naming standard in `AINotes/codingstandards.md` (e.g., `projects/mcp/github`).
2. **Choose the transport:**
   - **Native SSE servers** (preferred) – expose `/sse` directly and join `mcp-net`.
   - **Stdio-only tools** – build a bridge container using `add-bridge.sh` so the stdio server is re-exposed as SSE on an internal port.
3. **Compose file basics:**
   - Join at least `mcp-net`; add extra networks (e.g., `postgres-net`) as required.
   - Set resource limits (256 MB RAM) and a healthcheck that probes the service port.
   - Avoid publishing ports unless you need host debugging. If you publish, comment the mapping and disable it in production.

## 2. Verify the Service in Isolation
Before touching the central proxy:
1. `docker compose up -d` the new service.
2. Use `docker compose ps` to confirm the container reports `healthy`.
3. From a container on `mcp-net`, run `curl http://<service-host>:<port>/<service>/sse` (or `.../sse` for native servers) and ensure you get an `HTTP/1.1 200 OK` stream.
4. Tail the service logs (`docker logs <container> --tail 50`) to confirm there are no startup errors.

## 3. Register the Service with the Proxy
Use the management script rather than editing JSON by hand—this keeps backups and restart logic consistent.

```bash
cd /home/administrator/projects/mcp
source /home/administrator/secrets/mcp-proxy.env
./add-to-central.sh --service <name> --port <bridge-port> --add-auth --test --test-token "$MCP_PROXY_TOKEN"
```

- `--port` automatically constructs `http://mcp-<name>-bridge:<port>/<name>/sse`. Use `--url` if the backend already exposes a native SSE endpoint (e.g., `http://mcp-postgres:8686/sse`).
- Leave `--add-auth` enabled so the proxy forwards the bearer token; otherwise clients will see 401s when the proxy is locked down.
- The script validates JSON, makes a timestamped backup (`config.json.bak-*`), writes the update atomically, restarts `mcp-proxy`, and can run a smoke test (`--test`).

## 4. Regenerate Config Safely
`render-config.sh` now merges existing `mcpServers` entries, but you should still:
1. Run `cd /home/administrator/projects/mcp/proxy && ./render-config.sh` **after** adding services or rotating the token.
2. Confirm the new service persists in `config/config.json`.
3. Restart `mcp-proxy` if the script didn’t do it for you: `docker compose restart mcp-proxy`.

## 5. Update Client Configurations
1. Run `./sync-claude-config.sh` to refresh `~/.config/claude/mcp-settings.json` for the administrator account.
2. Share the LAN endpoint (`http://linuxserver.lan:9090/<service>/sse`) and token with other operators via secure channels; they can run the same sync script or manually update their MCP config.
3. Ask users to run `claude mcp list` and ensure the new `<service>-proxy` shows `✔ connected`.

## 6. Documentation Checklist
- Append the service to `mcp/proxy/status.md` under “Active Backends”.
- If this is a new class of tool, update `mcp/proxy/CLAUDE.md` architecture and operations sections.
- Create or refresh the service-specific `projects/mcp/<service>/CLAUDE.md` detailing configuration, credentials location, and troubleshooting.
- If secrets were added, document them in `/home/administrator/secrets/<service>.env` and ensure `chmod 600`.

## 7. Troubleshooting Tips
- **401 Unauthorized:** confirm `--add-auth` was used and the proxy config includes the correct `Authorization` header.
- **404 / invalid session:** typical when clients hit `localhost` instead of `linuxserver.lan`, or when the backend restarts mid-session. Re-run `sync-claude-config.sh` and restart the backend container.
- **Proxy lost registrations after token rotation:** rerun `add-to-central.sh` (with `--force`) and `render-config.sh`. The merge logic should now preserve entries, but keep backups handy.
- **Bridge healthcheck failing:** ensure the bridge image actually exposes `/service/sse` (see `mcp/filesystem/bridge/docker-compose.yml` for pattern) and that the underlying stdio tool is installed in the image.

## 8. Removal / Cleanup
When decommissioning a service:
1. `./remove-from-central.sh --service <name> --test` to update the proxy.
2. Stop and delete the service container (`docker compose down --volumes`).
3. Clean related secrets and documentation.
4. Regenerate configs and re-sync Claude to avoid stale entries.

Following this playbook keeps the proxy consistent, avoids overwriting live entries during token rotations, and ensures every MCP client sees the same curated set of tools.
