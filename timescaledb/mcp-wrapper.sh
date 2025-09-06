#!/bin/bash
# MCP TimescaleDB wrapper script for Claude integration

# Set default values if not provided
: ${TSDB_HOST:="localhost"}
: ${TSDB_PORT:="5433"}
: ${TSDB_DATABASE:="timescale"}
: ${TSDB_USER:="tsdbadmin"}
: ${TSDB_PASSWORD:="TimescaleSecure2025"}

exec docker run --rm -i \
  --name mcp-timescaledb-stdio \
  --network host \
  --env TSDB_HOST="${TSDB_HOST}" \
  --env TSDB_PORT="${TSDB_PORT}" \
  --env TSDB_DATABASE="${TSDB_DATABASE}" \
  --env TSDB_USER="${TSDB_USER}" \
  --env TSDB_PASSWORD="${TSDB_PASSWORD}" \
  mcp-timescaledb:latest