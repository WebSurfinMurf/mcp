# Plan to Resolve `mcp-fetch` Connection Failure (Authoritative)

This plan synthesizes all analyses to resolve the `mcp-fetch` connection failure. The root cause is a broken authentication layer due to an un-rendered template variable in the `mcp-proxy`'s configuration, caused by a variable name mismatch.

This plan will fix the configuration rendering, restart the services, and then perform a full end-to-end verification.

---

## Phase 1: Fix Configuration Rendering

This phase will correct the variable mismatch and safely re-render the `config.json` file.

**1. Correct the Secrets File:**
   - **Action:** Modify `/home/administrator/secrets/mcp-proxy.env` to use the correct variable name.
   - **Change:** Rename `PROXY_API_KEY` to `MCP_PROXY_TOKEN`.

**2. Update the Configuration Template:**
   - **Action:** Edit `/home/administrator/projects/mcp/proxy/config/config.template.json` to ensure the `fetch` service is included. This prevents it from being deleted by the render script.
   - **Goal:** The `mcpServers` object in the template should include the `fetch` entry.

**3. Render the Live Configuration:**
   - **Action:** Execute the `render-config.sh` script.
   - **Command:** `cd /home/administrator/projects/mcp/proxy && ./render-config.sh`

**4. Verify the Rendered Configuration:**
   - **Action:** Inspect the newly generated `config.json` file to confirm the token was replaced.
   - **Command:** `grep -v '${MCP_PROXY_TOKEN}' /home/administrator/projects/mcp/proxy/config/config.json`
   - **Goal:** The command should return success (exit code 0), proving the literal string is no longer present.

---

## Phase 2: Restart and Verify

This phase will apply the corrected configuration and perform a full, end-to-end verification.

**1. Restart the Proxy:**
   - **Action:** `docker restart mcp-proxy`
   - **Goal:** Force the proxy to load the new, correctly rendered configuration file.

**2. Source Secrets:**
   - **Action:** `source /home/administrator/secrets/mcp-proxy.env`
   - **Goal:** Load the `$MCP_PROXY_TOKEN` for use in verification commands.

**3. Verify Proxy Health and Route:**
   - **Action:** Check that the proxy container is healthy and that the route is responsive.
   - **Commands:**
     ```bash
     docker inspect mcp-proxy --format '{{.State.Health.Status}}'
     curl -i --max-time 5 -H "Authorization: Bearer $MCP_PROXY_TOKEN" -H "Accept: text/event-stream" http://localhost:9090/fetch/sse
     ```
   - **Goal:** The health status should be `healthy` and the `curl` command should return `HTTP/1.1 200 OK`.

**4. Verify CLI Connection:**
   - **Action:** Run `/mcp` in the Claude CLI.
   - **Note:** It is recommended to tail the proxy logs (`docker logs -f mcp-proxy`) in a separate terminal during this step to observe the incoming request.
   - **Success:** The `fetch` server shows as `✔ connected`. The issue is resolved.
   - **Failure:** If it still fails, proceed to the contingency plan.

---

## Phase 3: (Contingency) CLI State Refresh

This phase will only be executed if the CLI connection still fails after the proxy has been fixed.

**1. Remove Existing `fetch` Server:**
   - **Action:** `claude mcp remove fetch`

**2. Re-add `fetch` Server:**
   - **Action:** `claude mcp add-json fetch '{"type": "sse", "url": "http://localhost:9090/fetch/sse", "headers": {"Authorization": "Bearer $MCP_PROXY_TOKEN"}}'`

**3. Final Verification:**
   - **Action:** Run `/mcp` in the Claude CLI.
