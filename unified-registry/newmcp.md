# New MCP Direction: Dual-Mode Architecture

**Date**: 2025-09-08  
**Status**: Planning Phase

## Executive Summary

The new direction proposes abandoning the complex unified-tools approach in favor of a cleaner dual-mode architecture where each MCP service can operate in both:
1. **stdio mode** - For Claude Code integration
2. **SSE mode** - For HTTP/web client integration (LiteLLM, Open WebUI)

This approach respects MCP's stateful protocol requirements while providing flexibility for different clients.

## Core Architecture Principles

### 1. Unified Codebase, Multiple Interfaces
- Single Python script per MCP service containing core logic
- Mode selection via command-line arguments (`--mode sse` or `--mode stdio`)
- Shared configuration file for both modes

### 2. Clean Separation of Concerns
- **Core Logic**: The actual MCP tool functionality (database queries, file operations, etc.)
- **Interface Layer**: How the tool communicates (stdio for Claude, SSE for web)
- **Configuration**: External config file for runtime parameters

### 3. Deployment Pipeline
- Single `deploy.sh` script as unified entry point
- Handles setup, configuration, and mode selection
- Simplifies both development and production deployment

## Implementation Plan

### Phase 1: Create Base Framework (2 hours)

#### 1.1 Core MCP Base Class
```python
# mcp_base.py
class MCPService:
    def __init__(self, name, version):
        self.name = name
        self.version = version
        self.tools = {}
    
    def register_tool(self, name, handler, schema):
        self.tools[name] = {"handler": handler, "schema": schema}
    
    def process_tool_call(self, tool_name, arguments):
        # Core logic for executing tools
        pass
    
    def run_stdio_mode(self, config):
        # JSON-RPC over stdio implementation
        pass
    
    def run_sse_mode(self, config):
        # HTTP/SSE server implementation
        pass
```

#### 1.2 Deployment Script Template
```bash
#!/bin/bash
# deploy_mcp.sh - Universal MCP deployment script
# Handles both stdio (for Claude) and SSE (for web) modes
```

### Phase 2: Migrate Existing Services (4 hours)

#### 2.1 PostgreSQL Service
- Convert existing postgres MCP to dual-mode
- File: `mcp_postgres.py`
- Tools: list_databases, execute_sql, etc.
- Config: Database connection settings

#### 2.2 Filesystem Service  
- Convert filesystem MCP to dual-mode
- File: `mcp_filesystem.py`
- Tools: read_file, write_file, list_directory, etc.
- Config: Allowed paths, permissions

#### 2.3 GitHub Service
- Convert GitHub MCP to dual-mode
- File: `mcp_github.py`
- Tools: search_repositories, create_issue, etc.
- Config: API token, rate limits

### Phase 3: Create Unified Registry (2 hours)

#### 3.1 Service Registry
```python
# mcp_registry.py
SERVICES = {
    "postgres": {
        "script": "mcp_postgres.py",
        "docker_image": "crystaldba/postgres-mcp",
        "network": "postgres-net",
        "tools": ["list_databases", "execute_sql"]
    },
    "filesystem": {
        "script": "mcp_filesystem.py",
        "docker_image": "mcp/filesystem",
        "mounts": ["/home/administrator:/workspace"],
        "tools": ["read_file", "write_file", "list_directory"]
    },
    # ... other services
}
```

#### 3.2 Configuration Generator
```python
# generate_config.py
def generate_claude_config():
    # Generate mcp_servers.json for Claude Code
    pass

def generate_litellm_config():
    # Generate SSE endpoints for LiteLLM
    pass
```

### Phase 4: Integration Layer (3 hours)

#### 4.1 Claude Code Integration
- Generate `mcp_servers.json` with stdio commands
- Each service runs in stdio mode
- Direct JSON-RPC communication

#### 4.2 LiteLLM/Web Integration
- Deploy services in SSE mode
- Expose HTTP endpoints
- Handle streaming responses

### Phase 5: Testing & Documentation (2 hours)

#### 5.1 Test Suite
- Test both modes for each service
- Verify tool execution
- Check error handling

#### 5.2 Documentation
- Usage guide for both modes
- Configuration reference
- Troubleshooting guide

## Project Structure

```
/home/administrator/projects/mcp/unified-registry-v2/
├── core/
│   ├── mcp_base.py          # Base class for all MCP services
│   ├── mcp_registry.py      # Service registry and metadata
│   └── mcp_utils.py         # Shared utilities
├── services/
│   ├── mcp_postgres.py      # PostgreSQL MCP service
│   ├── mcp_filesystem.py    # Filesystem MCP service
│   ├── mcp_github.py        # GitHub MCP service
│   ├── mcp_monitoring.py    # Monitoring MCP service
│   └── config/
│       ├── postgres.ini     # PostgreSQL config
│       ├── filesystem.ini   # Filesystem config
│       └── github.ini        # GitHub config
├── deploy/
│   ├── deploy.sh            # Universal deployment script
│   ├── generate_config.py   # Config generator for clients
│   └── docker-compose.yml   # Docker deployment (optional)
├── tests/
│   ├── test_stdio.py        # stdio mode tests
│   └── test_sse.py          # SSE mode tests
└── README.md                # Project documentation
```

## Benefits of This Approach

### 1. Architectural Integrity
- Respects MCP's stateful protocol design
- Clean separation between core logic and interface
- Single source of truth for each service

### 2. Flexibility
- Works with both Claude Code (stdio) and web clients (SSE)
- Easy to add new modes (websocket, gRPC, etc.)
- Configuration-driven behavior

### 3. Maintainability
- One codebase per service to maintain
- Unified deployment process
- Consistent patterns across all services

### 4. Cost Optimization
- For Claude Code: Direct stdio, no middleware needed
- For web clients: SSE mode, efficient streaming
- No unnecessary API gateway overhead

## Migration Path

### Step 1: Proof of Concept
- Implement one service (postgres) with dual-mode
- Test with both Claude Code and curl/browser
- Validate the architecture

### Step 2: Full Migration
- Convert remaining services
- Create unified deployment pipeline
- Update documentation

### Step 3: Deprecate Old System
- Remove old unified-tools adapter
- Remove SSE proxy dependency for Claude
- Clean up legacy code

## Implementation Timeline

- **Week 1**: Base framework and PostgreSQL service
- **Week 2**: Filesystem and GitHub services
- **Week 3**: Remaining services and testing
- **Week 4**: Documentation and deployment

## Next Steps

1. **Immediate**: Create `unified-registry-v2` directory structure
2. **Today**: Implement base MCP class and PostgreSQL service
3. **Tomorrow**: Test dual-mode with Claude Code and SSE
4. **This Week**: Complete migration of all 3 working services

## Command Examples

### Running in stdio Mode (for Claude Code)
```bash
./deploy.sh setup postgres
./deploy.sh run postgres stdio
```

### Running in SSE Mode (for web clients)
```bash
./deploy.sh run postgres sse
# Access at http://localhost:8000/
```

### Configuration in Claude Code
```json
{
  "mcpServers": {
    "postgres": {
      "command": "/home/administrator/projects/mcp/unified-registry-v2/deploy/deploy.sh",
      "args": ["run", "postgres", "stdio"]
    }
  }
}
```

## Conclusion

This new direction provides a cleaner, more maintainable architecture that:
- Respects MCP's design principles
- Eliminates complex middleware
- Provides flexibility for different clients
- Reduces maintenance overhead
- Follows software engineering best practices

The dual-mode approach is the optimal solution for personal use where cost-saving is important while maintaining architectural integrity.

---
*Based on the advice to adopt a unified codebase with multiple deployment modes*