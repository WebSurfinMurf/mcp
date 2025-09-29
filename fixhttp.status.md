# TBXark HTTP Fix Status

## Task Tracker
- [x] Update docker-compose mount to `/config/config.json` and adjust command flag.
- [x] Confirm proxy config (`config.json`) final host/baseURL + optional version.
- [x] Host-side redeploy (`docker compose up -d --force-recreate`).
- [x] Fixed package version from `@0.2.3` (non-existent) to `@0.6.2` (working) - **ROOT CAUSE**
- [x] Re-enabled `"type": "streamable-http"` in proxy config for HTTP streaming
- [x] Successfully tested Streamable HTTP endpoint at `http://localhost:9090/filesystem/mcp`
- [x] Registered with Claude Code: `claude mcp add filesystem http://localhost:9090/filesystem/mcp -t http`
- [x] Validated 9 filesystem tools working (read_file, list_directory, etc.)
- [x] Update documentation with validation results.

## Resolution Summary
**Root Cause**: Package version `@modelcontextprotocol/server-filesystem@0.2.3` does not exist in npm registry. This caused npx subprocess to fail silently, resulting in no routes being registered by the proxy.

**Fix Applied**: Changed to version `0.6.2` (latest stable) and re-enabled streamable-http mode.

**Status**: ✅ **FULLY OPERATIONAL** - Filesystem MCP working via Streamable HTTP on port 9090

_Last updated: 2025-09-29 - RESOLVED_
