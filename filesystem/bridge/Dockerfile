FROM ghcr.io/tbxark/mcp-proxy:v0.39.1

# Install Node/npm for the filesystem MCP bridge
RUN apt-get update \ 
    && apt-get install -y --no-install-recommends nodejs npm \ 
    && rm -rf /var/lib/apt/lists/*

# Preinstall tool to avoid runtime network fetch
RUN npm i -g @modelcontextprotocol/server-filesystem@2025.8.21

WORKDIR /app
COPY config/config.json ./config.json

EXPOSE 9071
CMD ["/app/mcp-proxy"]
