# Current Status & Open Questions (2025-09-19)

## LiteLLM Admin UI
- Traefik routing is functioning: `/ui`, `/litellm-asset-prefix/_next/...`, `/schedule/model_cost_map_reload/status` all return 200 from the container.
- The static bundle shipped with the current LiteLLM image renders a Next.js 404 page. Rebuilding the dashboard inside the container (`npm install --include=dev && npm run build`) produces the same result.
- Conclusion: the regression is upstream. We need either a working UI export from LiteLLM or a downgrade to a version that still ships the correct bundle. Until then, `/ui/` will show the “404” placeholder even though routing works.

## MCP Integration
- Original goal (`CODEXMCP.md` / `litellm.md`): run unmodified upstream MCP servers via LiteLLM’s native MCP gateway, exposed to Codex CLI/Open WebUI/VS Code. No local patches to the downloaded packages.
- Current obstacles:
  * LiteLLM’s `/mcp/tools` only returns SSE heartbeat pings; no tool catalog has been confirmed.
  * The documentation suite under `projects/litellm/` shows massive deletions, so most MCP runbooks/scripts are gone. Need to confirm whether that was intentional before restoring or reauthoring.
  * UI instability (404 bundle) complicates MCP validation because the dashboard can’t be used to inspect configured servers.

## Proposed Focus
1. Obtain a known-good LiteLLM UI build (from a prior release or upstream fix). Without it, `/ui/` remains unusable even though routing issues are solved.
2. Re-evaluate MPC integration once the UI is working: verify stdio connectors (`postgres-mcp`, `mcp-server-filesystem`) enumerate tools; capture `mcp-diagnose.sh` output; document in MCP status files.
3. Scope: MCP access can remain limited to LAN (`*.linuxserver.lan`). No need to expose `/mcp` externally.

## Next Research
- Review `projects/mcp/CODEXMCP.md` and `projects/mcp/litellm.md` to realign with the original “out-of-the-box” plan.
- Search external references for LiteLLM UI regressions or MCP catalog issues in recent releases.
