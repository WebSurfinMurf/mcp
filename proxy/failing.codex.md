# MCP Proxy 404 Investigation Notes (Codex)

Observations
- `config/config.json` currently registers only `test`, `filesystem`, and `fetch` backends (`mcp/proxy/config/config.json:15`). There is no `postgres` entry, so the proxy cannot know about `/postgres/sse`; any request to `/postgres/sse` returns 404. The template-driven renderer (`mcp/proxy/render-config.sh:36`) rewrites the live config from `config/config.template.json`, which also lacks the postgres definition, so running it after adding the entry would delete it again.
- The documented client URL in the failure report uses `/servers/postgres/sse` (`mcp/proxy/failing.gemini.md:24`), but every current example in the repo (e.g. `mcp/proxy/status.md:59`) uses the shorter `/postgres/sse` form. TBXark's proxy exposes services at `/<service-id>/sse`; hitting `/servers/postgres/sse` never reaches the service, explaining the 404s and the silent logs.
- The `mcp-postgres` compose stack (`mcp/postgres/docker-compose.yml`) is geared for SSE (`--transport sse --sse-port 8686`) and would work once the proxy entry is restored and the correct path is used. Status notes already flag the container as unhealthy (`mcp/proxy/status.md:95`), which is consistent with the missing registration.

Suggested Fix Strategy
1. Add the postgres backend to the central config (and keep it there). Either extend `config/config.template.json` with a persistent `"postgres"` section or change `render-config.sh` to merge tokens into the existing config so manual additions survive token rotations. Then run `add-to-central.sh --service postgres --port 8686 --add-auth` (or equivalent) to register it.
2. Update client configurations/tests to use `http://linuxserver.lan:9090/postgres/sse` (or `.../timescaledb/sse`), not `/servers/...`. Verify with `curl -N` that the SSE stream opens via the proxy after registration.
3. Re-run health checks and adjust documentation: once the route works, mark the postgres service active in `status.md` and align the failure report (or replace it with the fix confirmation) so future readers do not retry the `/servers/` URL.

No changes were made; these notes outline how to remediate the reported 404 behaviour.
