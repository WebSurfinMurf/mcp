# MCP SSE Testing Harness

## Prerequisites
- Claude CLI configured with API key (`HOME=/home/administrator/projects` when invoked from scripts).
- Target Node SSE container running locally on the assigned port.

## Scripts
- `filesystem-smoke.sh`: runs stdio initialize and Claude CLI command to list workspace directory.

Add service-specific smoke scripts as additional SSE wrappers come online.
