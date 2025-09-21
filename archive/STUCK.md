# LiteLLM UI & MCP Status – 2025-09-19

## UI Regression
- LiteLLM’s Admin UI bundle (even in the official image) renders Next.js’s 404 page. Rebuilding the dashboard inside the container reproduces the same output, so the issue is upstream. Solution options: request a fixed release from LiteLLM or overlay a known-good UI export from a previous version.

## MCP Validation
- `/mcp/tools` still only emits heartbeat pings. Need a working UI and restored MCP scripts to verify tool catalogs without modifying upstream packages.

## Next Steps
1. Pull the latest official LiteLLM image (no custom build) and confirm the UI regression persists.
2. Overlay a known-good UI export (e.g., from an older release) while keeping official binaries untouched, so `/ui` works without modifying source packages.
3. With the UI restored, rerun MCP diagnostics (`mcp-diagnose.sh`) on the LAN host and update `projects/mcp/CODEXMCP.md` accordingly.
