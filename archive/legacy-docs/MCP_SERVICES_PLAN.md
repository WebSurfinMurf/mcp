# MCP Services Implementation Plan
*Created: 2025-09-07*
*Following Validate-First Philosophy*

## Current State Assessment

### Working Services (4/5)
1. ✅ **filesystem** - Docker-based
2. ✅ **monitoring** - Node.js local
3. ✅ **fetch** - Docker-based
4. ✅ **postgres** - Docker-based (fixed with DATABASE_URI)
5. ❌ **memory** - Node.js local (library dependency issue)

### Services to Add (3)
1. **n8n** - Node.js with wrapper script - **WORKING STANDALONE**
2. **playwright** - Node.js - **WORKING STANDALONE**
3. **timescaledb** - Python Docker - **NEEDS FIX** (initialization issue)

## Investigation Summary

### n8n MCP
- **Location**: `/home/administrator/projects/mcp/n8n/`
- **Type**: Node.js with bash wrapper
- **Wrapper**: `mcp-wrapper.sh` loads environment variables
- **Status**: ✅ Works standalone (tested with tools/list)
- **Dependencies**: Requires n8n API key from `$HOME/projects/secrets/n8n-mcp.env`

### Playwright MCP
- **Location**: `/home/administrator/projects/mcp/playwright/`
- **Type**: Node.js direct
- **Status**: ✅ Works standalone (tested with tools/list)
- **Dependencies**: Connects to playwright service at localhost:3000

### TimescaleDB MCP
- **Location**: `/home/administrator/projects/mcp/timescaledb/`
- **Type**: Python in Docker container
- **Wrapper**: `mcp-wrapper.sh` runs Docker container
- **Status**: ❌ Has initialization issues
- **Problem**: Needs proper MCP initialization sequence

## Implementation Approach

### Phase 1: Add Working Services First (n8n, playwright)

These services already work standalone, so adding them should be straightforward.

#### Step 1.1: Add n8n to proxy configuration
```json
"n8n": {
  "command": "bash",
  "args": ["/home/administrator/projects/mcp/n8n/mcp-wrapper.sh"],
  "env": {
    "N8N_URL": "http://localhost:5678",
    "N8N_API_KEY": "${N8N_API_KEY}"
  },
  "description": "n8n workflow automation"
}
```

#### Step 1.2: Add playwright to proxy configuration
```json
"playwright": {
  "command": "node",
  "args": ["/home/administrator/projects/mcp/playwright/src/index.js"],
  "env": {
    "PLAYWRIGHT_URL": "http://localhost:3000",
    "PLAYWRIGHT_WS_URL": "ws://localhost:3000"
  },
  "description": "Browser automation with Playwright"
}
```

### Phase 2: Fix TimescaleDB

#### Investigation Needed:
1. Why is initialization failing?
2. Is it the same MCP version compatibility issue?
3. Does the Docker wrapper interfere with stdio?

#### Potential Solutions:
1. Update the Python MCP server code to handle initialization properly
2. Use Node.js wrapper instead of Python
3. Run Python directly without Docker

### Phase 3: Fix Memory Service

#### Options:
1. **Containerize it** (like TimescaleDB) to avoid library issues
2. **Fix the library dependency** in the local environment
3. **Use a different embedding library** that doesn't require binary dependencies

## Validation Checkpoints

### Before Adding Each Service:
- [ ] Test service works standalone
- [ ] Verify all dependencies are available
- [ ] Check for port/network conflicts
- [ ] Ensure no duplicate container names

### After Adding Each Service:
- [ ] New service responds via SSE
- [ ] All previous services still work
- [ ] No error logs in proxy
- [ ] Can list tools from new service
- [ ] Can execute at least one tool

## Implementation Order

1. **Add n8n** (simplest, uses wrapper)
2. **Add playwright** (Node.js, no wrapper needed)
3. **Fix and add timescaledb** (needs debugging)
4. **Fix memory service** (separate issue from new services)

## Risk Assessment

### Low Risk:
- Adding n8n and playwright (already working)
- These use different ports/resources than existing services

### Medium Risk:
- TimescaleDB initialization issue might require code changes
- Memory service library issue might be complex

### Mitigation:
- Add services one at a time
- Test after each addition
- Keep backup of working configuration
- Document what works at each step

## Success Criteria

- All 7 services (excluding memory) accessible via SSE
- Each service can list its tools
- No unnamed containers created
- Clean logs without errors
- Can tear down and recreate from configuration

## Next Immediate Steps

1. Create updated configuration with n8n
2. Test with just n8n added
3. If successful, add playwright
4. Test both new services
5. Investigate TimescaleDB initialization issue
6. Document findings and update this plan