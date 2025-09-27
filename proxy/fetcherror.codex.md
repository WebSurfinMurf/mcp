# Feedback on `fetcherrorplan.md`

1. **Secrets path and variable mismatch.** The plan tells us to edit `/home/administrator/projects/admin/secrets/mcp-proxy.env` and rename `PROXY_API_KEY` to `MCP_PROXY_TOKEN`. Actual deployments use `/home/administrator/secrets/mcp-proxy.env` (note: no `projects/admin` segment) and already rely on `MCP_PROXY_TOKEN`; the render script (`render-config.sh:18-34`) sources that exact variable. Recommend correcting the path and verifying the current env file before renaming anything.

2. **Rendering step will delete service entries.** Running `./render-config.sh` rebuilds `config/config.json` solely from `config/config.template.json` (which only contains the `test` backend). If we follow Phase 1 as written we will erase the registered `fetch`/`filesystem` services. Plan needs an explicit warning to back up the live config or, better, update the template (or the script to merge) before rendering.

3. **Token placeholder already resolved.** The present `config/config.json` stores the real token string; there is no literal `${MCP_PROXY_TOKEN}` placeholder. Before taking action, plan should confirm whether the mismatch described in Phase 1 is still occurring. Otherwise the root cause may be elsewhere (client cache, hostname, etc.).

4. **Restart instructions assume local Docker control.** `docker restart mcp-proxy` will fail in environments without direct daemon access (e.g., the CLI sandbox). The plan should mention how to request approval or use compose from the host where Docker is available.

5. **Verification ignores proxy hostname binding.** Commands hardcode `http://localhost:9090/...`, but our proxy is documented at `http://linuxserver.lan:9090`. Readers running the CLI off-box will still fail even after the config fix. Recommend clarifying when to use `localhost` versus the LAN hostname.

6. **Phase 3 should start earlier if CLI cache suspected.** Removing and re-adding the server is a low-risk debugging step and arguably should happen before re-rendering configs that can cause regressions. Suggest reordering to attempt a CLI cache flush first, then tackle configuration changes if the issue persists.

7. **No mention of log inspection.** To confirm the authentication layer is repaired, the plan should also tail proxy logs or use `docker logs mcp-proxy` during the curl test. This provides immediate confirmation that requests reach the proxy and helps distinguish token issues from connectivity problems.

These adjustments will keep the remediation focused on the actual failure mode without inadvertently regressing working services.
