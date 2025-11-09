# MCP Code Executor - Sandboxed TypeScript/Python Execution Environment
# Multi-stage build for minimal image size

FROM node:20-alpine AS base

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    curl \
    bash \
    && ln -sf python3 /usr/bin/python

# Use existing node user (UID 1000, GID 1000)

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json ./

# Install Node dependencies
RUN npm install --only=production && \
    npm install -g tsx && \
    npm cache clean --force

# Copy application code
COPY client.ts ./
COPY executor.ts ./
COPY generate-wrappers.ts ./
COPY mcp-server.ts ./
COPY tsconfig.json ./

# Create workspace directories
RUN mkdir -p /workspace/servers /workspace/skills /workspace/examples /tmp/executions && \
    chown -R node:node /workspace /tmp/executions /app

# Switch to non-root user
USER node

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Expose executor API port
EXPOSE 3000

# Start executor service
CMD ["tsx", "executor.ts"]
