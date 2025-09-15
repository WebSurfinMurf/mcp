# MCP Infrastructure - Model Context Protocol Services

*Last Updated: 2025-09-14*
*Status: ✅ Microservice Orchestrator Complete - Browser Automation Integrated*

## Overview
**PLAYWRIGHT INTEGRATION COMPLETE**: Repository for MCP (Model Context Protocol) microservice orchestrator that provides Claude Code with **22 tools across 7 categories** via expert-validated integrations. Successfully implemented custom HTTP-native Playwright service following Priority #1 expert recommendation, replacing Microsoft's limited stdio implementation.

## Current State
The MCP infrastructure has achieved full browser automation integration:
- ✅ **Microservice Orchestrator** deployed at `/home/administrator/projects/mcp/server/`
- ✅ **22 total tools**: 15 centralized + 7 Playwright browser automation tools
- ✅ **Custom Playwright Service**: Expert-recommended HTTP-native replacement for Microsoft's implementation
- ✅ **7 Tool Categories**: database, storage, monitoring, web, filesystem, workflow-automation, browser-automation
- ✅ **HTTP/JSON-RPC communication**: Proven working between orchestrator ↔ microservices
- ✅ **Orchestrator pattern**: Thin Python wrappers coordinate with dedicated MCP containers
- ✅ **Security compliance**: All secrets secured in `/home/administrator/secrets/mcp-server.env`
- ✅ **Claude Code Bridge**: Fixed port mapping issue - tools accessible via `localhost:8001`
- ✅ **Expert Validation Complete**: Priority #1 recommendation fully implemented and operational

## Directory Structure
```
/home/administrator/projects/mcp/
├── archive/                 # Legacy implementations and documentation
│   ├── compose/            # SSE bridge infrastructure and deployment patterns
│   ├── legacy-docs/        # Phase docs, status files, troubleshooting guides
│   ├── old-compose/        # Previous docker-compose configurations
│   ├── unified-registry/   # Original unified registry approach
│   ├── unified-registry-v2/# Enhanced unified registry with Node.js shims
│   └── secure-proxy-admin/ # Secure proxy configurations
├── fetch/                  # Web content fetching service
├── filesystem/             # File operations service
├── memory-postgres/        # Vector memory service
├── monitoring/             # System monitoring and log analysis
├── n8n/                   # Workflow automation service
├── playwright-http-service/ # Custom HTTP-native Playwright service (Expert Priority #1)
├── postgres/               # PostgreSQL operations service
├── timescaledb/            # Time-series database service
├── CLAUDE.md              # This documentation
└── README.md              # Basic project info
```

## Individual MCP Services

### Integrated Tools Status
**✅ Implemented in Centralized Server (22 Total)**:
1. **PostgreSQL Tools (5)** - Database queries, list databases/tables, server info, database sizes
2. **MinIO S3 Tools (2)** - Object listing and content retrieval
3. **Monitoring Tools (2)** - Loki log search + Netdata system metrics
4. **Web Fetch Tools (1)** - HTTP/web content fetching with markdown conversion
5. **Filesystem Tools (2)** - Secure file operations with path restrictions
6. **Workflow Automation Tools (3)** - n8n integration via orchestrator pattern
7. **Browser Automation Tools (7)** - Custom HTTP-native Playwright service with full web automation capabilities

**📁 Available for Future Integration**:
- **memory-postgres/** - Vector memory storage
- **timescaledb/** - Time-series database operations (custom implementation)

**✅ Successfully Integrated**:
- **n8n/** - Workflow automation (3 orchestrator tools operational)
- **playwright-http-service/** - Browser automation (7 tools operational via custom HTTP service)

### Implementation Status
- **Architecture**: Centralized LangChain server with integrated tools
- **Deployment**: Single Docker Compose stack with OAuth2 proxy
- **Access**: Dual patterns (internal direct + external authenticated)
- **Integration**: Ready for Claude Code via HTTP API or direct tool calls
- **Documentation**: Complete operational docs in `/home/administrator/projects/mcp/server/`

## Architecture Approach

### Previous Approaches (Archived)
1. **Unified Registry**: Single adapter serving all tools - archived due to complexity
2. **SSE-Only Services**: Pure HTTP/SSE approach - archived as experimental
3. **Dual-Mode Deployment**: stdio + SSE hybrid - archived due to maintenance overhead
4. **Proxy Gateway**: Centralized SSE proxy - archived for simplicity

### Current Approach: Individual Services
- Each service directory contains a complete, standalone MCP implementation
- Services can be deployed and configured independently
- Direct integration with Claude Code via MCP protocol
- Simpler debugging and maintenance

## Getting Started

### Using the Centralized MCP Server
1. **Internal Access**: Use `http://mcp.linuxserver.lan` for development tools
2. **External Access**: Configure Keycloak client for `https://mcp.ai-servicers.com`
3. **API Integration**: Use REST endpoints at `/tools/{tool_name}` for direct access
4. **Agent Mode**: Use `/agent/invoke` for LangChain agent interactions
5. **Documentation**: Browse API docs at `/docs` endpoint

### Service Development Pattern
```bash
# Example service structure
/home/administrator/projects/mcp/{service}/
├── mcp-wrapper.sh          # Service deployment script
├── Dockerfile              # Container definition
├── requirements.txt        # Dependencies
├── service.py             # Main service implementation
├── models.py              # Data models and schemas
├── CLAUDE.md              # Service documentation
└── README.md              # Quick start guide
```

## Configuration

### Environment Variables
- Service-specific secrets: `/home/administrator/secrets/mcp-{service}.env`
- Follow security best practices (no hardcoded credentials)
- Use environment variable references in all configurations

### Claude Code Integration
- Configuration file: `~/.config/claude/mcp-settings.json`
- Add services individually as needed
- Each service registers its own tools and capabilities

### Container Naming Convention
- Container names: `mcp-{service}`
- Network isolation where appropriate
- Consistent logging and health check patterns

## Archived Components

### Legacy Documentation
- **Phase Documentation**: Implementation phases and status updates
- **Planning Documents**: Various architectural approaches and plans
- **Troubleshooting Guides**: Service-specific issue resolution
- **Configuration Files**: Old docker-compose and deployment configs

### Archived Implementations
- **Unified Registry**: Centralized tool registry approach
- **SSE Services**: Pure HTTP/SSE implementation
- **Proxy Gateway**: Centralized SSE proxy system
- **Admin Tools**: Legacy maintenance and migration scripts

## Next Steps

### Immediate Actions
1. **Keycloak Setup**: Configure client `mcp-server` in realm `main` for external access
2. **Tool Testing**: Verify all 10 integrated tools function correctly
3. **Claude Code Integration**: Configure MCP settings to use internal access endpoint
4. **Performance Testing**: Validate concurrent request handling and response times

### Development Workflow
1. Select a service directory (e.g., `postgres/`, `fetch/`)
2. Review archived implementations for patterns and lessons learned
3. Implement service following MCP protocol specifications
4. Create deployment scripts and documentation
5. Test integration with Claude Code
6. Document service capabilities and usage

### Future Considerations
- **Service Health Monitoring**: Implement health checks and status reporting
- **Unified Logging**: Centralized logging for all services
- **Performance Metrics**: Service usage and performance tracking
- **Auto-Discovery**: Dynamic service registration and discovery
- **Load Balancing**: Service scaling and load distribution

## Support Resources

### Documentation
- **MCP Protocol**: Official Model Context Protocol specifications
- **Archived Implementations**: Previous approaches in `archive/` directory
- **Service Examples**: Working examples in individual service directories

### Development Tools
- **Individual Service Development**: Each service is self-contained
- **Docker Support**: Container-based deployment for isolation
- **Environment Management**: Standardized secret management approach

### Troubleshooting
- **Clean State**: No running containers or processes to conflict with
- **Fresh Configuration**: Claude Code MCP settings reset to empty
- **Archived Solutions**: Previous troubleshooting guides available in archive

---
*Centralized MCP server operational - internal access working, external access pending Keycloak configuration*