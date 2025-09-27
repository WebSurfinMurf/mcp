# Critique of `first3.md`

1. **Phase 1 is outdated (service already live).** `first3.md:11-31` treats `mcp-fetch` as unregistered, instructing direct config edits. In reality the service already exists in `config/config.json`, so blindly repeating the steps risks clobbering the live configuration. Recommendation: rewrite this phase as a validation checklist (confirm bridge health, hit `http://linuxserver.lan:9090/fetch/sse`, ensure clients see the tools) instead of re-adding entries.

2. **Manual JSON editing bypasses safer workflows.** The doc tells readers to modify `config/config.json` directly (`first3.md:13-16`), but `render-config.sh` regenerates that file from the template and helper scripts (`add-to-central.sh`) exist to perform safe updates. Recommendation: replace the manual edit instructions with the helper command (`./add-to-central.sh --service fetch --port 9072 --add-auth`) and add a warning that regenerating the config will drop hand-written changes unless the template is also updated.

3. **Proxy target URL missing SSE suffix.** The proposed internal URL (`http://mcp-fetch-bridge:9072/`) omits `/fetch/sse`, so the proxy would still 404 even after the edit. Recommendation: document the correct SSE endpoint (`http://mcp-fetch-bridge:9072/fetch/sse`) and explain the `/<service>/sse` pattern used by TBXark’s proxy.

4. **Hardcoded bearer token contradicts security guidance.** Examples in `first3.md:22-29` rely on `changeme-token`, encouraging readers to paste real tokens into command history or documentation. Recommendation: reference the real value from `/home/administrator/secrets/mcp-proxy.env` (e.g., `source` the file just-in-time) and add an explicit “do not commit tokens” reminder.

5. **Verification steps are incomplete.** The curl probe lacks the `Accept: text/event-stream` header, the plan never inspects container health (`docker compose ps mcp-fetch-bridge`), and there is no guidance to check proxy logs. Recommendation: expand the verification section to include SSE-specific headers, container health checks, and log review so failures surface quickly.

6. **Phase 2 offers little actionable direction.** `first3.md:35-50` simply suggests “search the filesystem” for minio/n8n configs even though the directories are empty. Recommendation: clarify that no MCP servers exist yet, outline whether stdio→SSE bridge containers should be built (mirroring fetch/filesystem), and specify expected toolsets or integration goals for each service.

7. **Missing documentation follow-through.** The plan omits reminders to update `CLAUDE.md`, `status.md`, and the centralized service listings after new integrations land. Recommendation: append a closing section that lists the required documentation and monitoring updates to keep records aligned with the deployment.
