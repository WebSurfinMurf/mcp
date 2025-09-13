# MCP Infrastructure - Model Context Protocol Services

*Last Updated: 2025-09-13*
*Status: 🔄 Clean State - Ready for New Implementation*

## Overview
Repository for MCP (Model Context Protocol) services that provide Claude Code and other AI tools with programmatic capabilities. Following a complete cleanup, the infrastructure is now ready for a fresh, simplified implementation.

## Current State
The MCP infrastructure has been reset to a clean state:
- ✅ Legacy centralized tool servers removed (dualdeploy, sse, litellm-bridge, proxy-sse)
- ✅ All legacy documentation and configurations archived
- ✅ Individual service directories preserved and ready for development
- ✅ Docker containers and images cleaned up
- ✅ Claude Code MCP configuration reset

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
├── playwright/             # Browser automation service
├── postgres/               # PostgreSQL operations service
├── timescaledb/            # Time-series database service
├── CLAUDE.md              # This documentation
└── README.md              # Basic project info
```

## Individual MCP Services

### Available Service Directories
Each service directory contains the implementation for a specific MCP tool:

1. **fetch/** - HTTP/web content fetching with markdown conversion
2. **filesystem/** - Secure file operations with path restrictions
3. **postgres/** - PostgreSQL database operations and queries
4. **memory-postgres/** - Vector memory storage (needs dependency fixes)
5. **monitoring/** - System monitoring, log queries, and metrics
6. **n8n/** - Workflow automation and integration
7. **playwright/** - Browser automation and web scraping
8. **timescaledb/** - Time-series database operations

### Service Implementation Status
- **Architecture**: Individual service approach (centralized approaches archived)
- **Configuration**: Each service can be deployed independently
- **Integration**: Services can be connected to Claude Code via MCP protocol
- **Documentation**: Service-specific docs within each directory

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

### For New Implementation
1. **Choose a Service**: Start with one of the existing service directories
2. **Review Archive**: Check `archive/` for previous implementation patterns
3. **Configure Environment**: Set up service-specific environment variables
4. **Deploy Service**: Follow service-specific deployment instructions
5. **Register with Claude**: Add to Claude Code MCP configuration

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
1. **Service Selection**: Choose which MCP services to implement first
2. **Architecture Decision**: Confirm individual service approach vs. alternatives
3. **Development Priority**: Determine service development order
4. **Integration Strategy**: Plan Claude Code integration approach

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
*Clean slate implementation ready - choose your architecture and begin development*