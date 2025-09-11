#!/bin/bash
# Fixed MCP TimescaleDB wrapper script with standard naming

# Use standard container name
CONTAINER_NAME="mcp-timescaledb"

# Stop any existing container with same name
docker stop ${CONTAINER_NAME} 2>/dev/null || true
docker rm ${CONTAINER_NAME} 2>/dev/null || true

# Load environment variables from standardized secret file
if [ -f "/home/administrator/secrets/mcp-timescaledb.env" ]; then
    source /home/administrator/secrets/mcp-timescaledb.env
fi

# Set default values if not provided
: ${TSDB_HOST:="localhost"}
: ${TSDB_PORT:="5433"}
: ${TSDB_DATABASE:="timescale"}
: ${TSDB_USER:="tsdbadmin"}
: ${TSDB_PASSWORD:="TimescaleSecure2025"}

exec docker run --rm -i \
  --name "${CONTAINER_NAME}" \
  --network host \
  --env TSDB_HOST="${TSDB_HOST}" \
  --env TSDB_PORT="${TSDB_PORT}" \
  --env TSDB_DATABASE="${TSDB_DATABASE}" \
  --env TSDB_USER="${TSDB_USER}" \
  --env TSDB_PASSWORD="${TSDB_PASSWORD}" \
  mcp-timescaledb:latest