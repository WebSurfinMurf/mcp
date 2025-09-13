FROM node:20-alpine

# Install dependencies for healthcheck
RUN apk add --no-cache curl

WORKDIR /app

# Copy and install SSE wrapper dependencies first
COPY --from=wrapper /wrapper/package*.json /wrapper/
COPY --from=wrapper /wrapper/sse-wrapper.js /wrapper/
RUN cd /wrapper && npm install

# Copy package files for monitoring MCP
COPY package*.json ./

# Install monitoring dependencies
RUN npm ci --only=production || npm install

# Copy source code
COPY src ./src

# Set environment variables with defaults
ENV LOKI_URL=http://loki:3100
ENV NETDATA_URL=http://netdata:19999
ENV PORT=8080
ENV HOST=0.0.0.0

# Expose port for SSE
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run the MCP server with SSE wrapper
CMD ["node", "/wrapper/sse-wrapper.js", "node", "/app/src/index.js"]