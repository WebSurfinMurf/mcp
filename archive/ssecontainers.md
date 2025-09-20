# Standard MCP Server Implementation Plan - SSE Protocol Containers

**Project Goal**: Replace custom HTTP API MCP servers with standard MCP protocol containers using Server-Sent Events (SSE) for LiteLLM compatibility

**Date**: 2025-09-16
**Status**: Planning Phase
**Target**: 31 tools across 7 standard MCP servers with SSE endpoints

---

## Current State Analysis

### ❌ **Problem with Current Implementation**
- **Custom HTTP API**: All existing "MCP" containers use `/tools/{name}` REST API
- **LiteLLM Incompatible**: LiteLLM expects JSON-RPC over SSE/WebSocket, not REST
- **Non-Standard Protocol**: No standard MCP initialize/capabilities handshake
- **Cannot Register**: LiteLLM mcp_servers configuration fails with custom format

### ✅ **Working Tools to Migrate (31 total)**
- **PostgreSQL** (5): postgres_query, postgres_list_databases, postgres_list_tables, postgres_server_info, postgres_database_sizes
- **MinIO Storage** (2): minio_list_objects, minio_get_object
- **System Monitoring** (2): search_logs, get_system_metrics
- **Web Content** (1): fetch_web_content
- **Filesystem** (2): read_file, list_directory
- **n8n Workflow** (3): n8n_list_workflows, n8n_get_workflow, n8n_get_database_statistics
- **Playwright Browser** (7): navigate, screenshot, click, fill, get_content, evaluate, wait_for_selector
- **TimescaleDB Core** (2): tsdb_query, tsdb_database_stats
- **TimescaleDB Advanced** (7): tsdb_execute, tsdb_create_hypertable, tsdb_show_chunks, tsdb_compression_stats, tsdb_add_compression, tsdb_continuous_aggregate, tsdb_show_hypertables

---

## Target Architecture

### **Standard MCP Server Containers (8 Total)**

#### 1. **mcp-postgres**
- **Tools** (5): PostgreSQL operations
- **Container**: `mcp-postgres:latest`
- **SSE Endpoint**: `http://mcp-postgres:8080/sse`
- **Backend**: Direct PostgreSQL connections
- **Purpose**: PostgreSQL database operations

#### 2. **mcp-timescaledb**
- **Tools** (9): All TimescaleDB operations
- **Container**: `mcp-timescaledb:latest`
- **SSE Endpoint**: `http://mcp-timescaledb:8080/sse`
- **Backend**: TimescaleDB direct connections
- **Purpose**: Time-series database management

#### 3. **mcp-storage**
- **Tools** (2): MinIO object operations
- **Container**: `mcp-storage:latest`
- **SSE Endpoint**: `http://mcp-storage:8080/sse`
- **Backend**: MinIO S3 API connections
- **Purpose**: Object storage management

#### 4. **mcp-monitoring**
- **Tools** (2): Loki logs + Netdata metrics
- **Container**: `mcp-monitoring:latest`
- **SSE Endpoint**: `http://mcp-monitoring:8080/sse`
- **Backend**: Loki + Netdata HTTP APIs
- **Purpose**: System observability

#### 5. **mcp-fetch**
- **Tools** (1): Web content fetching
- **Container**: `mcp-fetch:latest`
- **SSE Endpoint**: `http://mcp-fetch:8080/sse`
- **Backend**: HTTP client with readability parsing
- **Purpose**: Web scraping and content extraction

#### 6. **mcp-filesystem**
- **Tools** (2): File operations
- **Container**: `mcp-filesystem:latest`
- **SSE Endpoint**: `http://mcp-filesystem:8080/sse`
- **Backend**: Local filesystem with security validation
- **Purpose**: Secure file access

#### 7. **mcp-n8n**
- **Tools** (3): n8n workflow operations
- **Container**: `mcp-n8n:latest`
- **SSE Endpoint**: `http://mcp-n8n:8080/sse`
- **Backend**: n8n API integration
- **Purpose**: Workflow automation

#### 8. **mcp-playwright**
- **Tools** (7): Browser automation operations
- **Container**: `mcp-playwright:latest`
- **SSE Endpoint**: `http://mcp-playwright:8080/sse`
- **Backend**: Playwright browser automation
- **Purpose**: Web browser automation

---

## Standard MCP Protocol Implementation

### **Required MCP Protocol Components**

#### 1. **SSE Endpoint Structure**
```
GET /sse HTTP/1.1
Accept: text/event-stream
Cache-Control: no-cache

# Response:
Content-Type: text/event-stream
Connection: keep-alive

data: {"jsonrpc": "2.0", "method": "initialize", ...}

```

#### 2. **JSON-RPC 2.0 Message Format**
```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "method": "tools/call",
  "params": {
    "name": "postgres_query",
    "arguments": {
      "query": "SELECT version();"
    }
  }
}
```

#### 3. **MCP Protocol Methods**
- **initialize**: Capability negotiation and protocol version
- **tools/list**: Discover available tools and their schemas
- **tools/call**: Execute specific tool with arguments
- **notifications**: Server-to-client notifications (optional)

#### 4. **Tool Schema Format**
```json
{
  "name": "postgres_query",
  "description": "Execute read-only PostgreSQL query",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "SQL query to execute"},
      "database": {"type": "string", "description": "Database name (optional)"}
    },
    "required": ["query"]
  }
}
```

---

## Implementation Plan

### **Phase 1: Infrastructure Setup (Week 1)**

#### Day 1-2: MCP Protocol Foundation
- [ ] Create base MCP server template with SSE endpoint
- [ ] Implement JSON-RPC 2.0 message handling
- [ ] Add MCP protocol initialization and capability exchange
- [ ] Create tool schema definition system
- [ ] Add comprehensive error handling and logging

#### Day 3-4: Container Architecture
- [ ] Design Docker container template for MCP servers
- [ ] Create shared MCP library for common functionality
- [ ] Implement health checks and monitoring
- [ ] Set up container networking and service discovery
- [ ] Create deployment scripts and environment management

#### Day 5-7: Testing Framework
- [ ] Create MCP protocol compliance testing
- [ ] Build SSE connection testing tools
- [ ] Implement tool execution validation
- [ ] Set up integration testing with mock LiteLLM
- [ ] Create performance benchmarking tools

### **Phase 2: Core Servers Implementation (Week 2)**

#### Day 8-10: Database Servers (Priority 1)
**mcp-database** (7 tools):
- [ ] Implement PostgreSQL connection pooling
- [ ] Add all 5 PostgreSQL tools with proper schemas
- [ ] Integrate TimescaleDB core tools (query, stats)
- [ ] Add comprehensive error handling for SQL operations
- [ ] Test with real database connections

**mcp-timeseries** (7 tools):
- [ ] Implement advanced TimescaleDB operations
- [ ] Add hypertable management tools
- [ ] Implement compression and continuous aggregates
- [ ] Add chunk management and statistics
- [ ] Test with TimescaleDB instance

#### Day 11-12: Storage and Monitoring (Priority 2)
**mcp-storage** (2 tools):
- [ ] Implement MinIO S3 client integration
- [ ] Add object listing and retrieval tools
- [ ] Implement security validation for object access
- [ ] Test with MinIO instance

**mcp-monitoring** (2 tools):
- [ ] Integrate Loki LogQL query system
- [ ] Add Netdata metrics collection
- [ ] Implement time-range and filtering options
- [ ] Test with observability stack

#### Day 13-14: Web and Filesystem (Priority 3)
**mcp-web** (1 tool):
- [ ] Implement web content fetching with readability
- [ ] Add robots.txt compliance checking
- [ ] Implement content length limits and security
- [ ] Test with various websites

**mcp-filesystem** (2 tools):
- [ ] Implement secure file operations with path validation
- [ ] Add directory listing with proper permissions
- [ ] Implement file size and content type validation
- [ ] Test with restricted file access

### **Phase 3: Automation Server (Week 3)**

#### Day 15-18: Complex Automation Server
**mcp-n8n** (3 tools):
- [ ] Integrate n8n API client for workflow operations
- [ ] Implement workflow listing and details retrieval
- [ ] Add database statistics and monitoring
- [ ] Test workflow management functionality

**mcp-playwright** (7 tools):
- [ ] Implement Playwright browser automation system
- [ ] Add persistent browser context management
- [ ] Implement screenshot and interaction tools
- [ ] Add JavaScript evaluation and form handling
- [ ] Test complete browser automation workflows

#### Day 19-21: Integration and Testing
- [ ] Deploy all 8 MCP servers in Docker environment
- [ ] Test SSE connections and protocol compliance
- [ ] Validate all 31 tools work correctly
- [ ] Perform load testing and performance optimization
- [ ] Create comprehensive documentation

### **Phase 4: LiteLLM Integration (Week 4)**

#### Day 22-24: LiteLLM Configuration
- [ ] Configure LiteLLM with all 8 MCP servers
- [ ] Test SSE transport connections
- [ ] Validate tool discovery and execution
- [ ] Test concurrent tool usage
- [ ] Optimize timeout and retry settings

#### Day 25-26: End-to-End Testing
- [ ] Test complete flow: OpenWebUI → LiteLLM → MCP Servers
- [ ] Validate all 31 tools accessible from OpenWebUI
- [ ] Test complex multi-tool workflows
- [ ] Performance testing under load
- [ ] Security validation and penetration testing

#### Day 27-28: Production Deployment
- [ ] Deploy to production environment
- [ ] Set up monitoring and alerting
- [ ] Create operational runbooks
- [ ] Document troubleshooting procedures
- [ ] Train users on new tool capabilities

---

## Technical Specifications

### **MCP Server Template Structure**
```
/mcp-{service}/
├── Dockerfile
├── requirements.txt
├── mcp_server.py          # Main MCP protocol implementation
├── tools/
│   ├── __init__.py
│   ├── tool1.py          # Individual tool implementations
│   └── tool2.py
├── schemas/
│   └── tools.json        # Tool schema definitions
├── config/
│   └── settings.py       # Configuration management
├── tests/
│   ├── test_protocol.py  # MCP protocol tests
│   └── test_tools.py     # Tool functionality tests
└── docker-compose.yml    # Service deployment
```

### **Environment Configuration**
```bash
# Shared across all MCP servers
MCP_PROTOCOL_VERSION=2024-11-05
MCP_LOG_LEVEL=INFO
MCP_TIMEOUT=30

# Service-specific (example for database)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=admin
POSTGRES_PASSWORD=Pass123qp
POSTGRES_DATABASE=postgres

TIMESCALE_HOST=timescaledb
TIMESCALE_PORT=5432
TIMESCALE_USER=tsdbadmin
TIMESCALE_PASSWORD=TimescaleSecure2025
TIMESCALE_DATABASE=timescale
```

### **Docker Network Configuration**
```yaml
networks:
  mcp-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.25.0.0/24

services:
  mcp-database:
    networks:
      - mcp-network
      - postgres-net
    expose:
      - "8080"

  # Similar for all MCP servers
```

---

## Resource Requirements

### **Development Time Estimate**
- **Phase 1** (Infrastructure): 40 hours
- **Phase 2** (Core Servers): 60 hours
- **Phase 3** (Automation): 30 hours
- **Phase 4** (Integration): 20 hours
- **Total**: ~150 hours over 4 weeks

### **Infrastructure Resources**
- **CPU**: 7 containers × 0.5 CPU = 3.5 CPU cores
- **Memory**: 7 containers × 512MB = 3.5GB RAM
- **Storage**: ~2GB for container images
- **Network**: Internal Docker networking only

### **Dependencies**
- **Existing Services**: PostgreSQL, TimescaleDB, MinIO, Loki, Netdata, n8n
- **Python Libraries**: fastapi, sse-starlette, asyncpg, boto3, httpx, playwright
- **Docker**: Latest version with compose support
- **Development Tools**: Python 3.11+, testing frameworks

---

## Success Criteria

### **Technical Requirements**
- [ ] All 31 tools implemented with standard MCP protocol
- [ ] SSE endpoints working with LiteLLM
- [ ] Sub-second response times for tool execution
- [ ] 99.9% uptime for MCP servers
- [ ] Complete tool schema validation
- [ ] Comprehensive error handling and logging

### **Integration Requirements**
- [ ] LiteLLM successfully discovers all 8 MCP servers
- [ ] OpenWebUI can execute all 31 tools through LiteLLM
- [ ] Concurrent tool execution without conflicts
- [ ] Proper authentication and authorization
- [ ] Complete audit logging of tool usage

### **Operational Requirements**
- [ ] Automated deployment and scaling
- [ ] Health monitoring and alerting
- [ ] Backup and disaster recovery procedures
- [ ] Performance monitoring and optimization
- [ ] Security compliance and validation

---

## Risk Mitigation

### **Technical Risks**
- **Risk**: MCP protocol complexity
  - **Mitigation**: Start with simple tools, use existing MCP libraries
- **Risk**: SSE connection stability
  - **Mitigation**: Implement reconnection logic, heartbeat monitoring
- **Risk**: Performance degradation
  - **Mitigation**: Connection pooling, caching, async operations

### **Operational Risks**
- **Risk**: Service dependencies
  - **Mitigation**: Health checks, graceful degradation, circuit breakers
- **Risk**: Configuration complexity
  - **Mitigation**: Environment templates, validation scripts, documentation
- **Risk**: Deployment issues
  - **Mitigation**: Staged rollouts, rollback procedures, testing environments

---

## Next Steps

### **Immediate Actions**
1. **Approve Plan**: Review and approve this implementation plan
2. **Resource Allocation**: Assign development time and infrastructure
3. **Create Repository**: Set up git repository with initial structure
4. **Start Phase 1**: Begin MCP protocol foundation implementation

### **Development Workflow**
1. **Daily Standups**: Track progress against plan
2. **Weekly Reviews**: Assess milestones and adjust timeline
3. **Testing Gates**: No phase progression without full testing
4. **Documentation**: Update docs continuously during development

### **Success Metrics**
- **Week 1**: MCP protocol foundation complete and tested
- **Week 2**: At least 4 MCP servers operational with 20+ tools
- **Week 3**: All 7 servers operational with 31 tools
- **Week 4**: Full LiteLLM integration and production deployment

---

**Timeline**: 4 weeks
**Outcome**: 31 tools accessible via 8 standard MCP servers with SSE protocol, fully integrated with LiteLLM
**Impact**: Universal AI tool access across all applications using LiteLLM proxy

### **Key Architecture Principles**
- **Each MCP Server = Separate Container**: Independent deployment and scaling
- **Standard MCP Protocol**: JSON-RPC 2.0 over Server-Sent Events (SSE)
- **LiteLLM Integration**: Direct registration via `mcp_servers` configuration
- **Remote Access**: All tools accessible remotely through SSE endpoints
- **Protocol Compliance**: Full MCP specification implementation for compatibility

*This plan transforms the custom HTTP API approach into industry-standard MCP protocol implementation, achieving the original goal of universal tool reusability through LiteLLM.*