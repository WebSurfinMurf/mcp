FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY core/ ./core/
COPY services/ ./services/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=postgresql://admin:Pass123qp@postgres:5432/postgres

# Default to SSE mode
CMD ["python", "-m", "services.mcp_postgres", "--mode", "sse"]