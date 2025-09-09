# MCP Dualdeploy Migration Plan

**Created**: 2025-09-09  
**Purpose**: Complete migration of all MCP services to dualdeploy architecture  
**Status**: Planning Phase - Awaiting Review  

## Executive Summary

Migrate all 7 active MCP services from proxy-sse to the dualdeploy dual-mode architecture, allowing each service to operate in both stdio mode (for Claude Code) and SSE mode (for LiteLLM/Open WebUI). This will replace the complex proxy-sse gateway with a cleaner, unified architecture.

## Current State Analysis

### What We Have Now

#### Dualdeploy (Working)
- **Location**: `/home/administrator/projects/mcp/dualdeploy/`
- **Architecture**: Python-based with dual-mode support (stdio/SSE)
- **Working Service**: postgres-v2 (5 tools, fully functional)
- **Components**:
  - `core/mcp_base.py` - Base class with datetime fix
  - `services/mcp_postgres.py` - PostgreSQL implementation
  - `shims/postgres.js` - Node.js bridge for Claude Code
  - `deploy.sh` - Deployment script

#### Proxy-SSE (To Be Replaced)
- **Location**: `/home/administrator/projects/mcp/proxy-sse/`
- **Port**: 8585
- **Services**: 7 services via different implementations
  - filesystem (Docker: `modelcontextprotocol/file-system`)
  - fetch (Docker: `mcp/fetch`)
  - postgres (Docker: different from dualdeploy)
  - monitoring (Node.js: native)
  - n8n (Node.js: with bash wrapper)
  - playwright (Node.js: native)
  - timescaledb (Docker: with bash wrapper)

### Services to Migrate

| Service | Current Implementation | Tools Count | Migration Strategy |
|---------|------------------------|-------------|-------------------|
| filesystem | Docker container | 4 | Python wrapper or native |
| fetch | Docker container | 1 | Python native (requests) |
| monitoring | Node.js | 5 | Python native (requests to Loki/Netdata) |
| n8n | Node.js + bash | 3 | Python native (n8n API) |
| playwright | Node.js | 4 | Python wrapper (subprocess) |
| timescaledb | Docker + bash | 3 | Python native (psycopg2) |
| github | npx (not in proxy) | 3 | Python native (PyGithub) |

## Proposed Architecture

### Service Implementation Strategies

#### Strategy A: Native Python Implementation (Preferred)
Best for services with Python libraries available:
- **fetch** → Use `requests` library
- **monitoring** → Use `requests` to query Loki/Netdata APIs
- **n8n** → Use `requests` for n8n REST API
- **timescaledb** → Use `psycopg2` (same as postgres)
- **github** → Use `PyGithub` library

#### Strategy B: Subprocess Wrapper
For services that must use existing implementations:
- **filesystem** → Could wrap Docker OR implement natively with `pathlib`
- **playwright** → Must wrap Node.js service (no good Python alternative)

### Directory Structure
```
/home/administrator/projects/mcp/dualdeploy/
├── core/
│   └── mcp_base.py              # Base class (existing)
├── services/
│   ├── mcp_postgres.py          # ✅ Existing
│   ├── postgres_models.py       # ✅ Existing
│   ├── mcp_filesystem.py        # To create
│   ├── filesystem_models.py     # To create
│   ├── mcp_fetch.py             # To create
│   ├── fetch_models.py          # To create
│   ├── mcp_monitoring.py        # To create
│   ├── monitoring_models.py     # To create
│   ├── mcp_n8n.py               # To create
│   ├── n8n_models.py            # To create
│   ├── mcp_playwright.py        # To create
│   ├── playwright_models.py     # To create
│   ├── mcp_timescaledb.py       # To create
│   ├── timescaledb_models.py    # To create
│   ├── mcp_github.py            # To create
│   └── github_models.py         # To create
├── shims/
│   ├── postgres.js              # ✅ Existing
│   ├── filesystem.js            # To create
│   ├── fetch.js                 # To create
│   ├── monitoring.js            # To create
│   ├── n8n.js                   # To create
│   ├── playwright.js            # To create
│   ├── timescaledb.js           # To create
│   └── github.js                # To create
├── deploy.sh                    # Update with new services
├── requirements.txt             # Update with new dependencies
└── PLAN.md                      # This file
```

## Implementation Plan

### Phase 1: Core Services (Native Python) - Week 1

#### 1.1 Filesystem Service
**Approach**: Native Python implementation
```python
# Key decisions needed:
# - Use pathlib for all file operations?
# - How to handle permissions/security?
# - Allowed paths configuration?
```

**Tools**:
- `list_directory` - Use `os.listdir()` or `pathlib`
- `read_file` - Use `open()` with size limits
- `write_file` - Use `open()` with atomic writes
- `create_directory` - Use `os.makedirs()`

**Questions**:
1. Should we keep Docker isolation or trust Python's path validation?
2. What paths should be allowed by default?
3. Should we support the same mount points as Docker version?

#### 1.2 Fetch Service
**Approach**: Native Python with `requests`
```python
# Simple implementation
import requests
from bs4 import BeautifulSoup  # For HTML to markdown
```

**Tools**:
- `fetch` - GET request with markdown conversion

**Questions**:
1. Should we add caching like the Docker version?
2. Rate limiting needed?
3. User-agent string to use?

#### 1.3 TimescaleDB Service
**Approach**: Extend PostgreSQL service
```python
# Reuse postgres connection pooling
# Add TimescaleDB-specific queries
```

**Tools**:
- `list_hypertables` - Query TimescaleDB catalog
- `query_timeseries` - Time-series specific queries
- `create_hypertable` - Create time-series tables

**Questions**:
1. Should this be separate or merged with postgres service?
2. Different port (5433) - how to handle multiple connections?
3. Need separate connection pool?

### Phase 2: API-Based Services - Week 1-2

#### 2.1 Monitoring Service
**Approach**: Native Python with `requests`
```python
# Query Loki and Netdata APIs
LOKI_URL = "http://loki:3100"
NETDATA_URL = "http://netdata:19999"
```

**Tools**:
- `search_logs` - LogQL queries to Loki
- `get_recent_errors` - Filtered log search
- `get_container_logs` - Container-specific logs
- `get_system_metrics` - Netdata API queries
- `check_service_health` - Health endpoints

**Questions**:
1. How to handle LogQL query building?
2. Should we cache metrics data?
3. Connection timeout settings?

#### 2.2 N8n Service
**Approach**: Native Python with `requests`
```python
# Use n8n REST API
N8N_API = "http://localhost:5678/api/v1"
```

**Tools**:
- `list_workflows` - GET /workflows
- `get_workflow` - GET /workflows/{id}
- `execute_workflow` - POST /workflows/{id}/execute

**Questions**:
1. API key from `/home/administrator/secrets/mcp-n8n.env`?
2. How to handle workflow execution results?
3. Async execution or wait for completion?

#### 2.3 GitHub Service
**Approach**: Native Python with `PyGithub`
```python
from github import Github
# Token from /home/administrator/secrets/github.env
```

**Tools**:
- `search_repositories` - Search GitHub repos
- `get_repository` - Get repo details
- `create_issue` - Create new issues

**Questions**:
1. Use PyGithub or raw REST API?
2. Rate limiting handling?
3. Which GitHub features to expose?

### Phase 3: Complex Service - Week 2

#### 3.1 Playwright Service
**Approach**: Subprocess wrapper (no good Python alternative)
```python
# Must wrap existing Node.js service
# Or use playwright-python (but different API)
```

**Tools**:
- `navigate` - Load URL
- `screenshot` - Capture page
- `click` - Click elements
- `fill` - Fill forms

**Questions**:
1. Keep Node.js subprocess or try playwright-python?
2. How to handle browser lifecycle?
3. Session management between calls?

## Migration Steps

### Step 1: Create Service Templates (Day 1)
```bash
# Create a template generator
python create_service_template.py filesystem
# Generates: mcp_filesystem.py, filesystem_models.py, filesystem.js
```

### Step 2: Implement Native Services (Days 2-4)
1. filesystem - Native Python
2. fetch - Native Python
3. timescaledb - Extend postgres
4. monitoring - Native Python
5. n8n - Native Python
6. github - Native Python

### Step 3: Implement Complex Service (Day 5)
1. playwright - Wrapper or playwright-python

### Step 4: Update Configuration (Day 6)
1. Update `deploy.sh` with all services
2. Create `register-all` command
3. Update `requirements.txt`

### Step 5: Testing (Day 7)
1. Test each service in stdio mode
2. Test each service in SSE mode
3. Integration test with Claude Code
4. Integration test with LiteLLM

### Step 6: Migration (Week 2)
1. Stop proxy-sse container
2. Register all services with Claude Code
3. Update LiteLLM configuration
4. Archive old directories

## Technical Decisions Needed

### 1. Service Implementation Philosophy
**Question**: Should we prioritize native Python implementations or wrap existing services?

**Option A**: Native Python everywhere possible
- ✅ Pros: Cleaner, faster, better error handling, single language
- ❌ Cons: Need to reimplement functionality, potential behavior differences

**Option B**: Wrap existing implementations
- ✅ Pros: Guaranteed compatibility, reuse tested code
- ❌ Cons: Subprocess overhead, complex error handling, multiple languages

**Recommendation**: Native Python except for Playwright

### 2. Configuration Management
**Question**: How should services load configuration?

**Option A**: Environment variables (current postgres approach)
- ✅ Pros: Standard, Docker-friendly, secure
- ❌ Cons: Need wrapper scripts, harder to manage

**Option B**: Config files (ini/yaml)
- ✅ Pros: Easier to manage, commented, structured
- ❌ Cons: Another file to maintain

**Option C**: Hybrid - env vars override config files
- ✅ Pros: Flexible, best of both
- ❌ Cons: More complex

**Recommendation**: Hybrid approach

### 3. Security Model
**Question**: How to handle filesystem access control?

**Option A**: Allowlist paths in config
```python
ALLOWED_PATHS = [
    "/home/administrator/projects",
    "/workspace",
    "/tmp/mcp-safe"
]
```

**Option B**: Docker container isolation
- Keep using Docker for filesystem service

**Option C**: OS-level permissions
- Run service as restricted user

**Recommendation**: Allowlist paths + validation

### 4. Dependencies
**New Python packages needed**:
```txt
requests>=2.31.0          # For fetch, monitoring, n8n
PyGithub>=2.1.1          # For GitHub service
beautifulsoup4>=4.12.0   # For HTML parsing
lxml>=4.9.0              # For HTML parsing
aiofiles>=23.2.1         # For async file operations
playwright>=1.40.0       # If using Python playwright
```

### 5. Service Registration
**Question**: How should services register with Claude Code?

**Option A**: Individual registration
```bash
./deploy.sh register filesystem
./deploy.sh register fetch
# ... etc
```

**Option B**: Bulk registration
```bash
./deploy.sh register-all
```

**Option C**: Auto-discovery
- Scan services/ directory
- Auto-generate configuration

**Recommendation**: Both A and B

## Risk Assessment

### High Risk Items
1. **Playwright service** - Complex browser automation, might need to keep Node.js
2. **Breaking changes** - Services might behave differently than originals
3. **Claude Code compatibility** - Shims must work perfectly

### Medium Risk Items
1. **Performance** - Python might be slower than Node.js for some operations
2. **Memory usage** - Multiple Python processes vs. single proxy
3. **Error handling** - Different error formats might break clients

### Low Risk Items
1. **Simple services** (fetch, github) - Straightforward to implement
2. **Database services** - Already proven with postgres
3. **API services** - Simple REST calls

## Success Criteria

### Phase 1 Success
- [ ] All 7 services implemented in Python
- [ ] All services work in stdio mode
- [ ] All services work in SSE mode
- [ ] All shims created and tested

### Phase 2 Success
- [ ] All services registered with Claude Code
- [ ] All services accessible via SSE for LiteLLM
- [ ] Proxy-sse container stopped
- [ ] Old directories archived

### Phase 3 Success
- [ ] Performance equal or better than proxy-sse
- [ ] Error handling improved
- [ ] Documentation complete
- [ ] No regression in functionality

## Questions for Review

### Critical Questions
1. **Is native Python implementation acceptable** for all services, or must we maintain exact compatibility with existing Docker/Node.js versions?

2. **Should filesystem service use Docker isolation** or is Python path validation sufficient for security?

3. **Should we merge TimescaleDB into PostgreSQL service** since they're both PostgreSQL-based?

4. **For Playwright, should we use playwright-python** (different API) or wrap the Node.js service?

5. **What's the priority order** for service migration? Should we do easy ones first or critical ones?

### Implementation Questions
1. **Configuration format**: Environment variables, config files, or hybrid?

2. **Logging strategy**: Where should services log? Stderr, files, or both?

3. **Error response format**: Match existing services exactly or improve?

4. **Connection pooling**: Share pools between services or separate?

5. **Testing strategy**: Unit tests, integration tests, or both?

### Deployment Questions
1. **Rollback plan**: How to quickly revert if something breaks?

2. **Parallel running**: Should we run both systems in parallel during migration?

3. **Monitoring**: How to ensure services are working after migration?

4. **Documentation**: Update existing docs or create new ones?

## Proposed Timeline

### Week 1 (Jan 9-15)
- Mon-Tue: Create templates and native Python services
- Wed-Thu: API-based services (monitoring, n8n, github)
- Fri: Playwright service and testing

### Week 2 (Jan 16-22)
- Mon-Tue: Integration testing and bug fixes
- Wed: Claude Code registration and testing
- Thu: LiteLLM configuration and testing
- Fri: Migration execution and monitoring

### Week 3 (Jan 23-29)
- Buffer for issues and documentation
- Performance optimization if needed
- Archive old systems

## Alternative Approaches

### Alternative 1: Keep Proxy-SSE for Web
- Only migrate Claude Code to dualdeploy
- Keep proxy-sse for LiteLLM/Open WebUI
- Pros: Less work, proven web integration
- Cons: Two systems to maintain

### Alternative 2: Node.js Shims for Everything
- Create Node.js shims that wrap existing services
- Don't reimplement in Python
- Pros: Guaranteed compatibility
- Cons: Not really "dual-mode", just proxying

### Alternative 3: Gradual Migration
- Migrate one service at a time
- Run hybrid system for weeks/months
- Pros: Lower risk, easy rollback
- Cons: Complex configuration, longer timeline

## Recommendation

**Recommended Approach**: Native Python implementation for all services except Playwright, with comprehensive testing before migration. This provides:

1. **Clean architecture** - Single language, single pattern
2. **Better maintainability** - No subprocess complexity
3. **Improved performance** - Direct execution, connection pooling
4. **Enhanced security** - Pydantic validation throughout
5. **Flexibility** - Easy to modify and extend

**Migration Strategy**: 
1. Implement all services in dualdeploy
2. Test thoroughly in parallel with existing system
3. Migrate Claude Code first (lower risk)
4. Migrate LiteLLM after validation
5. Keep proxy-sse as backup for 1 week
6. Archive after confirmation

## Next Steps

1. **Review this plan** with other AI for feedback
2. **Decide on critical questions** above
3. **Create service template generator**
4. **Begin implementation** with filesystem service
5. **Daily progress updates** in CLAUDE.md

## Appendix: Service Details

### Filesystem Service Specifics
```python
# Current Docker mounts
/workspace -> /home/administrator
/home/administrator/projects -> /home/administrator/projects (readonly)

# Proposed Python paths
ALLOWED_PATHS = [
    "/home/administrator/projects",  # Read-only
    "/home/administrator/workspace", # Read-write
    "/tmp/mcp-safe"                 # Temporary files
]
```

### Monitoring Service Specifics
```python
# Loki endpoints
GET /loki/api/v1/query_range  # LogQL queries
GET /loki/api/v1/series       # Series metadata
GET /loki/api/v1/labels       # Label names

# Netdata endpoints
GET /api/v1/data              # Metrics data
GET /api/v1/info              # System info
GET /api/v1/alarms            # Active alarms
```

### N8n Service Specifics
```python
# API endpoints
GET /api/v1/workflows          # List workflows
GET /api/v1/workflows/{id}     # Get workflow
POST /api/v1/workflows/{id}/execute  # Execute
GET /api/v1/executions         # List executions
```

### GitHub Service Specifics
```python
# PyGithub usage
from github import Github
g = Github(token)
repo = g.get_repo("owner/name")
issues = repo.get_issues(state="open")
```

### Playwright Service Specifics
```javascript
// Current Node.js service runs on port 3000
// Provides WebSocket and HTTP endpoints
// Manages browser lifecycle
// Handles multiple sessions
```

---

## Review Request

**To Other AI**: Please review this plan and provide feedback on:

1. **Architecture decisions** - Native Python vs. wrappers
2. **Security approach** - Path validation vs. Docker isolation
3. **Service priorities** - Which to implement first
4. **Risk mitigation** - How to handle potential issues
5. **Timeline feasibility** - Is 2 weeks realistic?
6. **Missing considerations** - What haven't I thought of?

**Specific concerns**:
- Is removing Docker isolation for filesystem too risky?
- Should we maintain 100% compatibility or improve where possible?
- How to handle service-specific configuration (API keys, endpoints)?
- Best approach for Playwright given its complexity?

---

*This plan represents a complete migration strategy from proxy-sse to dualdeploy architecture. Please review and provide feedback before implementation begins.*