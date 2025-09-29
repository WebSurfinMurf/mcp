# Feedback on `mcp/planhttp.md`

## Strengths
- ✅ Clear “no SSE” directive and stdio-preservation requirement.
- ✅ Inventory table captures current transport state per service.
- ✅ Adopt-the-proxy-first approach (TBXark) minimizes custom glue.
- ✅ Step-by-step filesystem rollout instructions (config.json, docker-compose). 

## Improvement Recommendations
1. **Filesystem config paths**
   - Make `/home/administrator/projects/mcp/proxy/config.json` directory in plan (mkdir command) before references.
   - Clarify whether relative paths inside Docker should be `/workspace/...`; highlight that the entire repo is mounted at `/workspace`.
2. **Port mapping & naming consistency**
   - Document final external port: plan suggests 9090 for proxy; update sequential port strategy (Phase 2) to reflect service name in URL rather than new host port per service (TBXark uses `/service-name/mcp`).
   - Rename `mcp-sse-net` to `mcp-http-net` consistently in requirements section.
3. **Claude configuration snippet**
   - Add specific `mcpServers` JSON entry showing `"type": "http"` with `/filesystem/mcp` endpoint.
4. **Remove “SSE fallback” references**
   - Since directive is “no new SSE”, ensure risk section says “retain SSE only if client explicitly requires it” and note that TBXark proxy already exposes `/sse` for legacy clients (we can keep it disabled if not needed).
5. **Monitoring & logging**
   - Suggest log collection path: TBXark container logs via Docker -> Loki; mention adding `/health` endpoint checks via proxy’s root.
6. **Clarify Phase 2 steps**
   - Emphasize adding each stdio server under `mcpServers` array rather than per-service port; show sample multi-entry config.
7. **Archive SSE plan**
   - Mention that `mcp/plansse.md` and `mcp/filesystem-sse/` will be archived/deleted once HTTP plan succeeds.

## Suggested next edits
- Add short code block for multi-service `config.json` with filesystem + minio entries.
- Provide explicit mkdir/compose commands in Phase 0 instructions.
- Update risk/mitigation section to say “legacy SSE served by proxy if enabled; otherwise disabled per security requirements”.

Work these changes into `mcp/planhttp.md` when convenient; content already strong overall.
