# PostgreSQL MCP SSE Service
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including PostgreSQL client
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/postgres/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy core framework
COPY core/ ./core/

# Copy service-specific code
COPY services/postgres/ ./

# Create non-root user
RUN groupadd -r mcpuser && useradd -r -g mcpuser mcpuser
RUN chown -R mcpuser:mcpuser /app

# Switch to non-root user
USER mcpuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${SERVICE_PORT}/health || exit 1

# Default port
EXPOSE 8001

# Run the service
CMD ["python", "service.py"]