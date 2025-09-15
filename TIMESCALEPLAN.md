# TimescaleDB HTTP-Native Service Conversion Plan

**Project**: Convert TimescaleDB MCP Service from stdio to HTTP-native Architecture
**Date**: 2025-09-14
**Status**: 🚧 **READY FOR IMPLEMENTATION**
**Problem**: Current service stuck in infinite logging loop causing restart cycle
**Solution**: Follow proven Playwright HTTP-native pattern

## 🎯 Executive Summary

**CURRENT ISSUE IDENTIFIED**: The TimescaleDB MCP service is stuck in an infinite logging loop, repeatedly printing "Connected to TimescaleDB" which causes container restarts every 40 seconds.

**SOLUTION APPROACH**: Convert from problematic stdio-based implementation to proven HTTP-native architecture, following the successful Playwright service pattern.

**EXPECTED OUTCOME**: Stable, production-ready TimescaleDB service with 9+ time-series tools integrated into the MCP orchestrator pattern.

## 📊 Current State Analysis

### ✅ **Problem Diagnosis Complete**
- **Issue**: Infinite logging loop in stdio-based Python service
- **Evidence**: `docker logs` shows repeated "Connected to TimescaleDB" messages
- **Container Status**: Restarting every 40 seconds (confirmed via `docker ps`)
- **Root Cause**: Flawed stdio MCP implementation with connection loop bug

### 📂 **Current Implementation Analysis**
- **Location**: `/home/administrator/projects/mcp/timescaledb/`
- **Architecture**: stdio-based Python MCP server with Docker wrapper
- **Tools Available**: 9 comprehensive time-series database tools
- **Database Connection**: Working (TimescaleDB on port 5433)
- **Integration Method**: Standalone stdio container (problematic)

### 🔧 **Available Tools to Migrate**
1. **tsdb_query** - Execute SELECT queries
2. **tsdb_execute** - Execute non-SELECT SQL commands
3. **tsdb_create_hypertable** - Convert tables to hypertables
4. **tsdb_show_hypertables** - List all hypertables with metadata
5. **tsdb_show_chunks** - Show chunks for hypertables
6. **tsdb_compression_stats** - View compression statistics
7. **tsdb_add_compression** - Add compression policies
8. **tsdb_continuous_aggregate** - Create continuous aggregate views
9. **tsdb_database_stats** - Get database statistics

## 🏗️ HTTP-Native Architecture Design

### **Technology Stack** (Following Playwright Pattern)
- **Runtime**: Python + Flask/FastAPI (HTTP server)
- **Database Driver**: asyncpg (already working in current implementation)
- **Container**: Python 3.11-slim base image
- **Communication**: HTTP REST API with JSON request/response
- **Integration**: MCP orchestrator pattern with thin Python wrappers

### **Service Architecture**
```
Claude Code → MCP Orchestrator → HTTP Request → TimescaleDB HTTP Service → Database Connection → Tool Execution
```

### **Design Principles**
1. **Persistent Database Connections**: Connection pool maintained across requests
2. **Request Isolation**: Each HTTP request gets isolated database transaction
3. **Error Resilience**: Comprehensive error handling with detailed logging
4. **Resource Management**: Proper connection pool cleanup and monitoring

## 📁 Implementation Structure

### **New Directory Layout**
```
/home/administrator/projects/mcp/timescaledb-http-service/
├── server.py                    # Main HTTP server (Flask/FastAPI)
├── database.py                  # Database connection and query logic
├── tools.py                     # Tool implementations (9 functions)
├── models.py                    # Request/response data models
├── Dockerfile                   # Container definition
├── requirements.txt             # Dependencies
├── docker-compose.yml           # Service definition for microservices stack
├── CLAUDE.md                    # Service documentation
└── README.md                    # Quick start guide
```

### **HTTP Endpoints Design**
- **Health**: `GET /health` - Service and database status
- **Info**: `GET /info` - Service information and available tools
- **Tools**: `GET /tools` - List all 9 available tools
- **Execution**: `POST /tools/{toolName}` - Execute specific tool

### **Request/Response Format**
```json
// Request
{
  "input": {
    "query": "SELECT * FROM hypertables LIMIT 5",
    "timeout": 30000
  }
}

// Response
{
  "tool": "tsdb_query",
  "result": {
    "success": true,
    "rows": [...],
    "row_count": 5,
    "execution_time_ms": 45
  },
  "requestId": 1757895116572,
  "timestamp": "2025-09-14T22:58:26.030Z",
  "status": "success"
}
```

## 🔧 Implementation Phases

### **Phase 1: HTTP Service Foundation** (Day 1)
1. **Create HTTP Service Structure**
   - Set up new directory: `timescaledb-http-service/`
   - Create Flask/FastAPI HTTP server framework
   - Implement health and info endpoints
   - Add basic error handling and logging

2. **Database Connection Layer**
   - Port existing asyncpg connection logic from `server.py`
   - Implement connection pool management
   - Add connection health checks
   - Fix the infinite logging loop bug

3. **Container Configuration**
   - Create Dockerfile with Python 3.11-slim base
   - Add TimescaleDB connection testing
   - Set up proper environment variable handling
   - Configure logging (structured JSON for Promtail)

### **Phase 2: Tool Implementation** (Day 2)
1. **Port Existing Tools**
   - Extract 9 tool functions from current `server.py`
   - Convert from MCP decorators to HTTP endpoint handlers
   - Implement request validation and error handling
   - Add comprehensive response formatting

2. **Tool Categories Implementation**
   - **Query Operations**: `tsdb_query`, `tsdb_execute`
   - **Hypertable Management**: `tsdb_create_hypertable`, `tsdb_show_hypertables`, `tsdb_show_chunks`
   - **Compression**: `tsdb_compression_stats`, `tsdb_add_compression`
   - **Advanced Features**: `tsdb_continuous_aggregate`, `tsdb_database_stats`

3. **Testing Implementation**
   - Create test endpoints for each tool
   - Implement database connectivity validation
   - Add request/response logging for debugging

### **Phase 3: MCP Orchestrator Integration** (Day 3)
1. **Update MCP Orchestrator**
   - Add TimescaleDB HTTP service to `docker-compose.microservices.yml`
   - Create 9 thin Python wrapper tools in main orchestrator
   - Implement HTTP client calls from orchestrator to TimescaleDB service
   - Add proper error handling and timeout configuration

2. **Tool Registration**
   - Add TimescaleDB tools to centralized tool list
   - Update tool categorization (add `time-series-database` category)
   - Ensure tools are properly exposed via localhost:8001
   - Update Claude Code bridge integration

3. **Security & Configuration**
   - Secure database credentials in `/home/administrator/secrets/mcp-server.env`
   - Implement connection validation and timeout protection
   - Add request logging and monitoring capabilities

### **Phase 4: Testing & Validation** (Day 4)
1. **End-to-End Testing**
   - Test all 9 tools via HTTP endpoints directly
   - Validate tools via MCP orchestrator integration
   - Verify Claude Code bridge exposes all TimescaleDB tools
   - Performance testing (response times, connection pooling)

2. **Container Management**
   - Deploy via microservices Docker Compose stack
   - Verify health checks and container stability
   - Test service restart and recovery procedures
   - Monitor resource usage and connection pool behavior

3. **Documentation Updates**
   - Create comprehensive service documentation
   - Update LANGNEXT.md with TimescaleDB HTTP service achievement
   - Document tool usage examples and troubleshooting
   - Update SYSTEM-OVERVIEW.md with new container inventory

## 🔒 Security & Configuration

### **Database Security**
```python
# Enhanced connection configuration
DB_CONFIG = {
    "host": os.getenv("TSDB_HOST", "timescaledb"),  # Internal Docker hostname
    "port": int(os.getenv("TSDB_PORT", "5432")),   # Internal port, not 5433
    "database": os.getenv("TSDB_DATABASE", "timescale"),
    "user": os.getenv("TSDB_USER"),
    "password": os.getenv("TSDB_PASSWORD"),
    "min_size": 2,                                  # Connection pool minimum
    "max_size": 10,                                 # Connection pool maximum
    "command_timeout": 60,                          # Query timeout
    "server_settings": {
        "application_name": "mcp-timescaledb-http"
    }
}
```

### **Security Controls**
- **Query Validation**: SQL injection prevention through parameterized queries
- **Resource Limits**: Connection pool limits and query timeouts
- **Error Handling**: Sanitized error messages (no credential exposure)
- **Access Control**: HTTP service only accessible via internal Docker network
- **Audit Logging**: All queries logged with request IDs for traceability

## 📈 Expected Benefits

### **Stability Improvements**
- **No More Restart Loop**: HTTP service eliminates stdio communication issues
- **Persistent Connections**: Database connection pool maintained across requests
- **Better Error Handling**: HTTP status codes and structured error responses
- **Resource Efficiency**: No process spawning overhead per request

### **Performance Gains**
- **Connection Pooling**: Reuse database connections across requests
- **Faster Response Times**: No container initialization overhead
- **Concurrent Requests**: Multiple simultaneous database operations
- **Optimized Queries**: Connection pool optimization for time-series workloads

### **Integration Benefits**
- **Consistent Architecture**: Matches proven Playwright HTTP-native pattern
- **Easier Debugging**: HTTP logs, request tracing, and status monitoring
- **Scalability**: Can handle multiple concurrent MCP orchestrator requests
- **Maintainability**: Standard HTTP service patterns familiar to developers

## 🆚 Architecture Comparison

| Feature | Current stdio Implementation | New HTTP-Native Service |
|---------|------------------------------|-------------------------|
| **Communication** | stdio (problematic) | HTTP (proven stable) |
| **Database Management** | Connection per container spawn | Persistent connection pool |
| **Error Handling** | stdio stream errors | HTTP status codes + JSON |
| **Performance** | High overhead (container spawn) | Optimized (persistent service) |
| **Debugging** | Complex stdio debugging | Standard HTTP logging |
| **Integration** | Standalone MCP container | Orchestrator pattern |
| **Stability** | Restart loop issues | Proven stable architecture |

## 🧪 Testing Strategy

### **Unit Testing**
- **Database Connection**: Test connection pool creation and cleanup
- **Tool Functions**: Test each of the 9 tools with sample data
- **Error Handling**: Test malformed requests and database errors
- **Security**: Test SQL injection prevention and input validation

### **Integration Testing**
- **HTTP Endpoints**: Test all endpoints with various payloads
- **MCP Orchestrator**: Test tool calls via orchestrator pattern
- **Claude Code Bridge**: Verify all tools accessible via localhost:8001
- **Performance**: Load testing with concurrent requests

### **End-to-End Testing**
```bash
# Health check
curl http://localhost:8080/health

# Test hypertable listing
curl -X POST http://localhost:8080/tools/tsdb_show_hypertables \
  -H "Content-Type: application/json" \
  -d '{"input": {}}'

# Test via MCP orchestrator
curl -X POST http://localhost:8001/tools/tsdb_show_hypertables \
  -H "Content-Type: application/json" \
  -d '{"input": {}}'
```

## 🎯 Success Criteria

### **Technical Metrics**
- ✅ **Container Stability**: Service runs without restarts for 24+ hours
- ✅ **Tool Availability**: All 9 TimescaleDB tools operational via HTTP
- ✅ **Response Time**: <500ms average for simple queries
- ✅ **Connection Pooling**: Efficient database connection reuse
- ✅ **Error Handling**: Graceful error responses with proper HTTP status codes

### **Integration Validation**
- ✅ **MCP Orchestrator**: All tools callable via orchestrator pattern
- ✅ **Claude Code Bridge**: All tools exposed via localhost:8001
- ✅ **Tool Categorization**: Properly categorized as "time-series-database"
- ✅ **Documentation**: Complete service documentation and usage examples

### **Operational Excellence**
- ✅ **Monitoring**: Health checks and logging working correctly
- ✅ **Resource Usage**: Optimal memory and CPU usage patterns
- ✅ **Security**: No credential exposure in logs or error messages
- ✅ **Maintainability**: Clear code structure and comprehensive documentation

## 🔄 Migration Strategy

### **Parallel Deployment**
1. **Keep Current Service Running**: Don't disrupt existing functionality
2. **Deploy HTTP Service**: Add as new container in microservices stack
3. **Test HTTP Service**: Validate all functionality working
4. **Switch Orchestrator**: Update orchestrator to use HTTP service
5. **Remove stdio Service**: Clean up old container after validation

### **Rollback Plan**
```bash
# If HTTP service fails, rollback to stdio version
cd /home/administrator/projects/mcp/server
docker compose -f docker-compose.microservices.yml down mcp-timescaledb-http
# stdio version continues running as fallback
```

### **Environment Variables Migration**
```bash
# Update /home/administrator/secrets/mcp-server.env
# Add TimescaleDB HTTP service configuration
TIMESCALEDB_HTTP_ENDPOINT=http://mcp-timescaledb-http:8080
TSDB_HOST=timescaledb
TSDB_PORT=5432
TSDB_DATABASE=timescale
TSDB_USER=tsdbadmin
TSDB_PASSWORD=TimescaleSecure2025
```

## 📋 Implementation Checklist

### **Phase 1: Foundation**
- [ ] Create `timescaledb-http-service/` directory structure
- [ ] Implement Flask/FastAPI HTTP server with health endpoints
- [ ] Port database connection logic and fix logging loop
- [ ] Create Dockerfile and test container build
- [ ] Add to microservices Docker Compose stack

### **Phase 2: Tools**
- [ ] Port all 9 tools from stdio implementation to HTTP endpoints
- [ ] Implement request validation and error handling
- [ ] Add comprehensive logging and request tracing
- [ ] Test all tools directly via HTTP endpoints

### **Phase 3: Integration**
- [ ] Create 9 thin wrapper tools in MCP orchestrator
- [ ] Update Docker Compose to include TimescaleDB HTTP service
- [ ] Test all tools via orchestrator pattern
- [ ] Verify Claude Code bridge integration

### **Phase 4: Production**
- [ ] Deploy complete microservices stack with HTTP TimescaleDB service
- [ ] Validate container stability (no restart loops)
- [ ] Performance testing and optimization
- [ ] Update documentation and SYSTEM-OVERVIEW.md

## 🚀 Expected Timeline

- **Day 1**: HTTP service foundation and database connection fix
- **Day 2**: Tool implementation and testing
- **Day 3**: MCP orchestrator integration and validation
- **Day 4**: Production deployment and documentation

**Total Estimated Time**: 4 days for complete HTTP-native TimescaleDB service

## 🏆 Achievement Target

**Goal**: Transform problematic stdio-based TimescaleDB service into production-ready HTTP-native service, following proven Playwright pattern.

**Success Metrics**:
- 🎯 **31 Total Tools**: 22 current + 9 TimescaleDB = comprehensive toolset
- 🎯 **8 Tool Categories**: Add "time-series-database" to existing 7 categories
- 🎯 **Zero Restart Issues**: Stable container operation
- 🎯 **Expert Architecture**: HTTP-native microservice pattern validated

---

**Status**: 🚧 **READY FOR IMPLEMENTATION**
**Next Step**: Begin Phase 1 - HTTP Service Foundation
**Expected Completion**: 4 days
**Dependencies**: TimescaleDB container (operational), MCP orchestrator (operational), Docker Compose microservices stack (operational)