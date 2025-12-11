FROM python:3.12-slim

WORKDIR /app

# Install system dependencies + Docker CLI for gateway control
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    ca-certificates \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    ib-mcp \
    ib-async \
    fastmcp \
    fastapi \
    uvicorn[standard] \
    pydantic

# Copy server code
COPY src /app/src

# Copy configuration
COPY config /app/config

EXPOSE 8000

CMD ["python3", "/app/src/server.py"]
