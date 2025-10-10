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
