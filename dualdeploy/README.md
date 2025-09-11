# MCP Dual-Mode Services

Clean implementation of dual-mode MCP services that work with both Claude Code (stdio) and web clients (SSE).

## Quick Start

```bash
# Setup
./deploy.sh setup

# Register with Claude Code
./deploy.sh register postgres

# Restart Claude Code, then test:
# "Using postgres-v2, list all databases"
```

## Available Services

- **postgres** - PostgreSQL database operations (5 tools)

## Documentation

See [CLAUDE.md](CLAUDE.md) for full documentation.

## Directory Structure

- `core/` - Base MCP service class
- `services/` - Service implementations
- `shims/` - Node.js shims for Claude Code
- `deploy.sh` - Deployment script