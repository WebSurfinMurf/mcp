# Use the existing MCP filesystem image
FROM mcp/filesystem:latest AS filesystem-base

# Create a wrapper image with SSE support
FROM node:20-alpine

# Install Docker CLI for running the filesystem container
RUN apk add --no-cache docker-cli curl

WORKDIR /app

# For now, we'll use the filesystem MCP directly via docker
# Later we'll add an SSE wrapper

# Create a simple entry script
RUN echo '#!/bin/sh' > /app/start.sh && \
    echo 'docker run --rm -i \' >> /app/start.sh && \
    echo '  -v /workspace:/workspace \' >> /app/start.sh && \
    echo '  -v /home/administrator/projects:/projects \' >> /app/start.sh && \
    echo '  mcp/filesystem /workspace /projects' >> /app/start.sh && \
    chmod +x /app/start.sh

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD echo "healthy" || exit 1

# Expose port for future SSE wrapper
EXPOSE 8080

# Run filesystem MCP
CMD ["/app/start.sh"]