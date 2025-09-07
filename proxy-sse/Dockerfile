FROM ghcr.io/sparfenyuk/mcp-proxy:latest

# Install Node.js and Docker CLI for MCP servers
USER root
RUN apk add --no-cache nodejs npm docker-cli bash

# Stay as root for now since we need to run Docker commands
WORKDIR /app
