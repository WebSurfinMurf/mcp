FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    ib-mcp \
    ib-insync \
    fastmcp

# Copy configuration
COPY config /app/config

# Create startup script
RUN echo '#!/bin/bash\n\
exec python -m ib_mcp.server \
    --host ${IB_HOST:-mcp-ib-gateway} \
    --port ${IB_PORT:-4002} \
    --client-id ${IB_CLIENT_ID:-1}' > /app/start.sh && \
    chmod +x /app/start.sh

EXPOSE 3000

CMD ["/app/start.sh"]
