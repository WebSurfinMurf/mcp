# Filesystem MCP SSE Service
FROM python:3.11-slim

# Install system dependencies  
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY services/filesystem/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared core framework
COPY core/ ./core/

# Copy service-specific files
COPY services/filesystem/ ./

# Create non-root user for security
RUN groupadd -r mcpuser && useradd -r -g mcpuser mcpuser
RUN chown -R mcpuser:mcpuser /app

USER mcpuser

# Expose service port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Start service
CMD ["python", "service.py"]