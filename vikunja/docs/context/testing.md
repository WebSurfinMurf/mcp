# Testing

## Current State
- No dedicated test files in mcp/vikunja project
- Tested via pipecat's test_mcp_scoping.py (102 tests covering tool injection, schema stripping, identity injection)
- Manual testing via MCP JSON-RPC calls

## Test Coverage (via pipecat)
- Tool schema visibility (username stripped, project_name visible)
- Identity injection (username auto-injected into Vikunja tool calls)
- Priority and due_date parameter handling
- Project name resolution flow

## Known Gaps
- No unit tests for vikunja_client.py
- No tests for user auto-creation flow
- No tests for project auto-creation flow
- No tests for JWT minting/caching
- No integration tests against running Vikunja instance
