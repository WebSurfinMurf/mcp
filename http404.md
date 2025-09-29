# Streamable HTTP 404 Investigation (TBXark/mcp-proxy)

**Date:** 2025-09-28

## Summary
Attempts to reach Streamable HTTP endpoints through TBXark/mcp-proxy consistently return `HTTP 404`, despite the proxy successfully launching the filesystem stdio MCP server. Both root (`/mcp`) and service-prefixed (`/filesystem/mcp`) URLs fail. Proxy logs indicate only an SSE server is listening. We need to determine whether the proxy build supports Streamable HTTP for stdio services, what configuration is required, and whether additional flags or version pinning are necessary.

## Environment
- Proxy image: `ghcr.io/tbxark/mcp-proxy:latest` (pulled on 2025-09-28)
- Running with:
  ```bash
  docker run --rm -p 9190:9190 \
    -v /home/administrator/projects:/workspace \
    -v /home/administrator/projects/mcp/proxy/config.json:/config.json \
    ghcr.io/tbxark/mcp-proxy:latest --config /config.json
  ```
- `config.json`:
  ```json
  {
    "mcpProxy": {
      "addr": ":9190",
      "baseURL": "http://127.0.0.1:9190",
      "name": "Local MCP Proxy",
      "options": {
        "logEnabled": true,
        "panicIfInvalid": false
      }
    },
    "mcpServers": {
      "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
      }
    }
  }
  ```

## Symptoms
- `filesystem-proxy-deploy.sh` restarts the proxy, then probes:
  - `GET /` → 404
  - `GET /filesystem/mcp` → 404
  - `POST /mcp` (initialize/tools/list) → 404
- Proxy container log (tail):
  ```
  2025/09/29 01:24:32 Starting sse server
  2025/09/29 01:24:32 sse server listening on :9190
  2025/09/29 01:24:32 <filesystem> Connecting
  ```
- No mention of HTTP transport; only SSE.
- `docker exec mcp-proxy-test npx --version` yields Node 20.11.1 (npx available).

## Observations & conflicting documentation
1. **Gemini feedback:** stdio services should be accessible at `POST /filesystem/mcp`; our tests still return 404.
2. **Claude feedback:** claims proxy only exposes `/service/sse`; suggests testing SSE endpoint with optional auth token. Our configuration lacks auth requirements, but the proxy still returns 404 for `/filesystem/mcp` and `/mcp`.
3. Our configuration matches the README example: `mcpProxy` with name/addr, `mcpServers` command launching filesystem server.
4. Proxy log explicitly says "Starting sse server", but no log indicates HTTP listener.

## Outstanding questions
- Does the `latest` Docker image include Streamable HTTP support for stdio services, or do we need a specific version (e.g., `v0.39.1`)?
- Is an environment flag or config option required to enable HTTP transport (e.g., `STREAMABLE_HTTP_ENABLED`)?
- Should we use the `"type": "stdio"` default rather than setting `streamable-http` (which seemed to make the service appear under `/mcp` but still returned 404)?
- Does the proxy aggregate stdio services under `/mcp` or `/service/mcp` in the current release?
- Is there a known issue/bug in current build causing missing HTTP handler while SSE remains active?

## Data to share with community/maintainers
- Configuration snippet (above)
- Proxy logs showing only SSE server startup
- `docker run` command used
- `curl` probes and resulting 404 responses
- `npx` availability confirmed inside container

## Next steps proposed
1. Ask maintainers which image tag or config enables Streamable HTTP for stdio.
2. Confirm proper induction by toggling `options.logEnabled`, checking for HTTP-specific log lines.
3. Try pinning to `ghcr.io/tbxark/mcp-proxy:v0.39.1` or building from source (if latest tag missing feature).
4. Verify whether SSE endpoints work (`GET /filesystem/sse`) to confirm the proxy is otherwise functional.

---
*Prepared by Codex to solicit help from TBXark proxy maintainers / community.*