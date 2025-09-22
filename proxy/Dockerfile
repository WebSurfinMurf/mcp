# Start from the official mcp-proxy image
FROM ghcr.io/tbxark/mcp-proxy:latest

# Switch to the root user to install packages
USER root

# Install the Docker CLI client and its dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends docker.io && \
    rm -rf /var/lib/apt/lists/*

# Switch back to the original non-root user for security
USER 1000