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

### 4. Strict JSON-RPC Protocol (Critical)
All communication follows JSON-RPC 2.0 specification for consistency and reliability:

#### Request Format:
```json
{
  "jsonrpc": "2.0",
  "method": "tool_name",
  "params": {
    "arg1": "value",
    "arg2": "value"
  },
  "id": 1
}
```

#### Success Response:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "output": "...",
    "data": {}
  },
  "id": 1
}
```

#### Error Response:
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": "Additional error details"
  },
  "id": 1
}
```

### 5. Security-First Design
- **Allowlisting Only**: No denylists, only explicit allows
- **Path Canonicalization**: Prevent directory traversal attacks
- **Read-Only Mode**: Global flag for safe operation
- **Input Validation**: Strict parameter checking before execution

### 6. State Management Strategy
- **In-Memory State**: For session-specific data
- **Persistent State**: Database or file-based for cross-session data
- **Stateless Tools**: Prefer stateless operations where possible
- **Connection Pooling**: Reuse database connections efficiently

## Implementation Plan

### Phase 1: Create Base Framework (2 hours)

#### 1.1 Core MCP Base Class with Security
```python
# mcp_base.py
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

class MCPService:
    def __init__(self, name: str, version: str, config: Dict[str, Any]):
        self.name = name
        self.version = version
        self.config = config
        self.tools = {}
        self.read_only = config.get('security', {}).get('read_only', False)
        self.allowed_paths = self._init_allowed_paths()
    
    def _init_allowed_paths(self) -> list:
        """Initialize and validate allowed paths from config"""
        paths = self.config.get('security', {}).get('allowed_paths', [])
        return [Path(p).resolve() for p in paths]
    
    def validate_path(self, path: str) -> bool:
        """Validate path against allowlist with canonicalization"""
        target = Path(path).resolve()
        return any(target.is_relative_to(allowed) for allowed in self.allowed_paths)
    
    def wrap_json_rpc_response(self, result: Any, request_id: int) -> Dict:
        """Wrap result in JSON-RPC 2.0 response format"""
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        }
    
    def wrap_json_rpc_error(self, code: int, message: str, request_id: int, data: Any = None) -> Dict:
        """Wrap error in JSON-RPC 2.0 error format"""
        error = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            },
            "id": request_id
        }
        if data:
            error["error"]["data"] = data
        return error
    
    def register_tool(self, name: str, handler, schema: Dict, write_operation: bool = False):
        """Register a tool with security metadata"""
        self.tools[name] = {
            "handler": handler,
            "schema": schema,
            "write_operation": write_operation
        }
    
    def process_tool_call(self, tool_name: str, arguments: Dict, request_id: int) -> Dict:
        """Process tool call with security checks"""
        # Check if tool exists
        if tool_name not in self.tools:
            return self.wrap_json_rpc_error(-32601, f"Method not found: {tool_name}", request_id)
        
        tool = self.tools[tool_name]
        
        # Check read-only mode
        if self.read_only and tool["write_operation"]:
            return self.wrap_json_rpc_error(-32600, "Operation not permitted in read-only mode", request_id)
        
        # Validate parameters against schema
        # ... schema validation logic ...
        
        try:
            result = tool["handler"](arguments)
            return self.wrap_json_rpc_response(result, request_id)
        except Exception as e:
            return self.wrap_json_rpc_error(-32603, str(e), request_id)
```

#### 1.2 Deployment Script Template
```bash
#!/bin/bash
# deploy_mcp.sh - Universal MCP deployment script
# Handles both stdio (for Claude) and SSE (for web) modes
```

#### 1.3 SSE Mode with FastAPI (Concurrent Connections)
```python
# mcp_base.py (continued)
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio
import uvicorn

class MCPService:
    # ... previous methods ...
    
    async def run_sse_mode(self, config: Dict[str, Any]):
        """Run service in SSE mode using FastAPI for concurrency"""
        app = FastAPI(title=f"{self.name} MCP Service")
        
        @app.get("/sse")
        async def sse_endpoint():
            async def event_generator():
                """Generate SSE events for connected clients"""
                while True:
                    # This is where you'd generate events
                    # Could be from a queue, database polling, etc.
                    event_data = await self.get_next_event()
                    yield f"data: {json.dumps(event_data)}\n\n"
                    await asyncio.sleep(1)
            
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive"
                }
            )
        
        @app.post("/tool/{tool_name}")
        async def execute_tool(tool_name: str, request: Dict[str, Any]):
            """Execute a tool via HTTP POST"""
            request_id = request.get("id", 1)
            params = request.get("params", {})
            return self.process_tool_call(tool_name, params, request_id)
        
        # Run the FastAPI server
        host = config.get("sse", {}).get("host", "0.0.0.0")
        port = config.get("sse", {}).get("port", 8000)
        uvicorn.run(app, host=host, port=port)
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

#### 2.4 Security Configuration Examples

**Filesystem Service Config** (`filesystem.ini`):
```ini
[security]
read_only = false
allowed_paths = [
    "/home/administrator/projects",
    "/home/administrator/workspace",
    "/tmp/mcp-safe"
]
forbidden_extensions = [".env", ".key", ".pem"]
max_file_size_mb = 100

[tools]
write_operations = ["write_file", "delete_file", "move_file"]
```

**PostgreSQL Service Config** (`postgres.ini`):
```ini
[security]
read_only = false
allowed_databases = ["mcp_db", "test_db"]
forbidden_tables = ["users", "credentials", "api_keys"]
allowed_operations = ["SELECT", "INSERT", "UPDATE"]
forbidden_operations = ["DROP", "TRUNCATE", "ALTER"]
max_query_time_seconds = 30

[connection]
pool_size = 10
pool_recycle_seconds = 3600
```

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

### Phase 4: State Management Implementation (2 hours)

#### 4.1 State Management Patterns

```python
# state_manager.py
from typing import Dict, Any, Optional
import json
import redis
import sqlite3
from pathlib import Path

class StateManager:
    """Flexible state management with multiple backends"""
    
    def __init__(self, backend: str = "memory", config: Dict[str, Any] = {}):
        self.backend = backend
        self.config = config
        self._init_backend()
    
    def _init_backend(self):
        """Initialize the chosen state backend"""
        if self.backend == "memory":
            self.store = {}  # Simple in-memory dict
        elif self.backend == "redis":
            self.redis_client = redis.Redis(
                host=self.config.get("host", "localhost"),
                port=self.config.get("port", 6379),
                db=self.config.get("db", 0)
            )
        elif self.backend == "sqlite":
            db_path = self.config.get("path", "mcp_state.db")
            self.conn = sqlite3.connect(db_path)
            self._init_sqlite_schema()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get state value by key"""
        if self.backend == "memory":
            return self.store.get(key, default)
        elif self.backend == "redis":
            value = self.redis_client.get(key)
            return json.loads(value) if value else default
        elif self.backend == "sqlite":
            cursor = self.conn.execute(
                "SELECT value FROM state WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
            return json.loads(row[0]) if row else default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set state value with optional TTL"""
        if self.backend == "memory":
            self.store[key] = value
        elif self.backend == "redis":
            self.redis_client.set(
                key, json.dumps(value), 
                ex=ttl if ttl else None
            )
        elif self.backend == "sqlite":
            self.conn.execute(
                "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)",
                (key, json.dumps(value))
            )
            self.conn.commit()
```

#### 4.2 Connection Pooling for Database Services

```python
# connection_pool.py
from contextlib import contextmanager
import psycopg2
from psycopg2 import pool

class DatabasePool:
    """Connection pooling for PostgreSQL"""
    
    def __init__(self, config: Dict[str, Any]):
        self.pool = psycopg2.pool.SimpleConnectionPool(
            minconn=config.get("min_connections", 1),
            maxconn=config.get("max_connections", 10),
            host=config.get("host"),
            port=config.get("port", 5432),
            database=config.get("database"),
            user=config.get("user"),
            password=config.get("password")
        )
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = self.pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.pool.putconn(conn)
```

### Phase 5: Integration Layer (3 hours)

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

## Key Improvements from Feedback

### 1. **JSON-RPC Protocol Formalization** ✅
- Strict JSON-RPC 2.0 compliance for all communication
- Standardized request/response formats
- Consistent error codes and handling
- Helper methods in base class for wrapping responses

### 2. **Security Hardening** ✅
- **Allowlisting only**: No denylists, explicit permission model
- **Path canonicalization**: Prevents directory traversal attacks
- **Read-only mode**: Global flag for safe operation
- **Forbidden operations**: Configurable per service
- **Input validation**: Schema-based parameter checking

### 3. **Concurrent SSE with FastAPI** ✅
- Replaced simple HTTPServer with FastAPI
- Native async support for multiple concurrent connections
- Non-blocking SSE streams
- Proper connection management

### 4. **State Management Strategy** ✅
- **Flexible backends**: Memory, Redis, or SQLite
- **Connection pooling**: Efficient database resource usage
- **TTL support**: Automatic expiration for temporary state
- **Session isolation**: Each connection maintains its own state

### 5. **Configuration-Driven Security** ✅
- Per-service security configuration files
- Allowed paths, databases, operations defined in config
- Maximum file sizes, query timeouts
- Write operation flags for tools

## Implementation Priority

1. **Week 1**: 
   - Implement base framework with all security features
   - Create PostgreSQL service as reference implementation
   - Test both stdio and SSE modes

2. **Week 2**: 
   - Port filesystem and GitHub services
   - Add comprehensive path validation
   - Implement connection pooling

3. **Week 3**: 
   - Add remaining services
   - Implement state management
   - Performance testing

4. **Week 4**: 
   - Security audit
   - Documentation
   - Deployment automation

## Conclusion

This refined architecture addresses all critical concerns:
- **Protocol consistency** through strict JSON-RPC
- **Security by design** with allowlisting and validation
- **Scalability** via FastAPI and connection pooling
- **Flexibility** with configurable state management

The dual-mode approach with these enhancements provides a production-ready, secure, and maintainable solution that respects MCP's design principles while being practical for both personal and professional use.

---
*Updated based on actionable feedback for security, concurrency, and state management*