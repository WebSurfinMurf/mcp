# Plan: Integrate and Verify MCP Services (Definitive Production Plan)

This document is the definitive, robust plan to verify and integrate the `mcp-fetch`, `mcp-minio`, and `mcp-n8n` services with the `mcp-proxy`. It incorporates feedback from multiple LLM analyses and prioritizes verification, safe configuration management, security, and operational clarity.

---

## Phase 0: Environment Validation & Preparation

This phase ensures the environment is correctly set up, required tools are present, and we have a safe baseline for modifications.

**1. Establish Lockfile:**
   - **Action:** `lockfile="/tmp/mcp-integration.lock"; if [[ -f "$lockfile" ]]; then echo "ERROR: Another integration is already running (PID: $(cat $lockfile))"; exit 1; fi; echo $$ > "$lockfile"; trap 'rm -f "$lockfile"' EXIT`
   - **Goal:** Prevent concurrent executions of this plan.

**2. Verify Dependencies:**
   - **Action:** `command -v docker >/dev/null || { echo "ERROR: Docker not found"; exit 1; } && command -v curl >/dev/null || { echo "ERROR: curl not found"; exit 1; }`
   - **Goal:** Confirm all required command-line tools are installed.

**3. Source and Validate Secrets:**
   - **Action:** `source /home/administrator/secrets/mcp-proxy.env; if [[ -z "$MCP_PROXY_TOKEN" || ${#MCP_PROXY_TOKEN} -lt 10 ]]; then echo "ERROR: MCP_PROXY_TOKEN is missing or invalid"; exit 1; fi`
   - **Goal:** Load the `$MCP_PROXY_TOKEN` into the shell and validate it.

**4. Backup Configuration:**
   - **Action:** `cp /home/administrator/projects/mcp/proxy/config/config.json "/home/administrator/projects/mcp/proxy/config/config.json.bak-$(date +%Y%m%d-%H%M%S)"`
   - **Goal:** Create a timestamped backup of the current, working proxy configuration.

**5. Verify Docker Network:**
   - **Action:** `docker network inspect mcp-net >/dev/null || { echo "ERROR: mcp-net network not found"; exit 1; }`
   - **Goal:** Ensure the `mcp-net` network exists and is ready.

---

## Phase 1: Verify Existing `mcp-fetch` Integration

This phase verifies the health and end-to-end configuration of the already-integrated `mcp-fetch` service.

**1. Verify `mcp-fetch-bridge` Container Health:**
   - **Action:** `docker compose -f /home/administrator/projects/mcp/fetch/bridge/docker-compose.yml ps`
   - **Goal:** Confirm the container is `running` and its status is `healthy`.

**2. Verify Direct Connection & Discover Path:**
   - **Action:** `FETCH_PATH="/fetch/sse"; docker run --rm --network=mcp-net curlimages/curl:latest -i --max-time 10 http://mcp-fetch-bridge:9072$FETCH_PATH || { echo "ERROR: Direct connection to fetch service failed"; exit 1; }`
   - **Goal:** Receive an `HTTP/1.1 200 OK` response with `Content-Type: text/event-stream`. This confirms the service is healthy and its path is `/fetch/sse`.

**3. Verify Proxy Route:**
   - **Action:** `curl -i --max-time 5 -H "Authorization: Bearer $MCP_PROXY_TOKEN" -H "Accept: text/event-stream" http://localhost:9090$FETCH_PATH || { echo "ERROR: Proxy route for fetch failed"; exit 1; }`
   - **Goal:** Receive an `HTTP/1.1 200 OK` response, confirming the proxy is routing correctly.

**4. Verify CLI Connection:**
   - **Action:** Run `/mcp` in the Claude CLI and inspect the `fetch` server entry.
   - **Goal:** The server should show a `✔ connected` status.

---

## Phase 2: Discover and Assess `mcp-minio` & `mcp-n8n`

This phase will determine the status and MCP compatibility of the remaining services.

**1. Discover Running Containers:**
   - **Action:** `docker ps -a --format "table {{.Names}}	{{.Image}}	{{.Ports}}	{{.Networks}}" | grep -iE "(minio|n8n|object.?storage|workflow|automation)"`
   - **Goal:** Identify container names, exposed ports, and attached networks for `minio` and `n8n`.

**2. Perform MCP Compatibility Test:**
   - For each discovered container, attempt a direct connection from within its network.
   - **Action (Example for minio):** `docker run --rm --network=<MINIO_NETWORK> curlimages/curl:latest -i --max-time 10 http://<MINIO_CONTAINER>:<MINIO_PORT>/`
   - **Goal:** Determine if the service responds with a `Content-Type: text/event-stream` header. If not, it is not MCP-compatible and requires a custom bridge.

---

## Phase 3: Integrate Compatible Services

This phase will only be executed for services that passed the MCP compatibility test.

**1. Update Proxy Configuration Template:**
   - **Action:** Edit `/home/administrator/projects/mcp/proxy/config/config.template.json` to add the new service entry (e.g., `minio`).
   - **Goal:** Ensure the new configuration is persistent.

**2. Render and Preview the Live Configuration:**
   - **Action:** `cd /home/administrator/projects/mcp/proxy && ./render-config.sh`
   - **Action:** `echo "Configuration changes to be applied:"; diff -u config/config.json.bak-* config/config.json || true; read -p "Apply these changes? (y/N): " -n 1 -r; echo; [[ $REPLY =~ ^[Yy]$ ]] || { echo "Changes cancelled"; exit 1; }`
   - **Goal:** Safely update the live `config.json` after a manual review of the changes.

**3. Restart and Verify:**
   - **Action:** `docker restart mcp-proxy`
   - **Goal:** Restart the proxy to load the new configuration. Then, perform the same end-to-end verification steps outlined in Phase 1 for the newly added service.

---

## Rollback Procedure

If any step results in a non-functional state, revert to the last known good configuration.

- **Action:** `LAST_BACKUP=$(ls -t /home/administrator/projects/mcp/proxy/config/config.json.bak-* | head -1); echo "Reverting to $LAST_BACKUP"; cp "$LAST_BACKUP" /home/administrator/projects/mcp/proxy/config/config.json`
- **Action:** `docker restart mcp-proxy`
- **Goal:** Restore the most recent backup and restart the proxy to return to a working state.