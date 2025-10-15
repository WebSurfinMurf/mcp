# ArangoDB MCP Server
# Using the standard arango-server package (TypeScript)
# Package: arango-server v0.4.0 by ravenwits
# Source: https://github.com/ravenwits/mcp-server-arangodb

FROM node:20-slim

WORKDIR /app

# Install arango-server MCP package
RUN npm install -g arango-server

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Health check script (arango-server doesn't have a health endpoint, check process)
RUN echo '#!/bin/sh\npgrep -f arango-server > /dev/null || exit 1' > /health.sh && chmod +x /health.sh

# Expose port (arango-server uses stdio by default, no port needed for container-internal usage)
# SSE transport not supported by this server, uses stdio only
EXPOSE 8000

# Run MCP server (stdio mode)
CMD ["arango-server"]
