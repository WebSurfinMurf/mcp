#!/bin/bash
set -euo pipefail

WORKDIR="/home/administrator/projects"
PROXY_DIR="$WORKDIR/mcp/proxy"
LOG_DIR="$WORKDIR/mcp/logs"
LOG_FILE="$LOG_DIR/filesystem-proxy-$(date +%Y%m%d-%H%M%S).log"
SERVICE_URL="http://localhost:9190/filesystem/mcp"

mkdir -p "$LOG_DIR"

{
  echo "=== Filesystem Proxy Deployment ==="
  date
  echo

  echo "--- Ensure network exists ---"
  docker network create mcp-http-net 2>/dev/null || true

  echo "--- Restart proxy container ---"
  docker rm -f mcp-proxy-test 2>/dev/null || true
  docker run -d --name mcp-proxy-test \
    --network mcp-http-net \
    -p 9190:9190 \
    -v "$WORKDIR:/workspace" \
    -v "$PROXY_DIR/config.json:/config.json" \
    ghcr.io/tbxark/mcp-proxy:latest --config /config.json

  echo "--- Wait for container startup (10s) ---"
  sleep 10

  echo "--- Proxy logs (tail) ---"
  docker logs --tail 40 mcp-proxy-test || true
  echo

  echo "--- POST initialize ---"
  curl -sS -i -X POST "$SERVICE_URL" \
    -H 'Content-Type: application/json' \
    -d '{"jsonrpc":"2.0","id":"init","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{}}}' || true
  echo

  echo "--- POST tools/list ---"
  HTTP_CODE=$(curl -sS -o /tmp/proxy-response.json -w "%{http_code}" \
    -X POST "$SERVICE_URL" \
    -H 'Content-Type: application/json' \
    -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}')
  cat /tmp/proxy-response.json
  echo
  echo "HTTP status: $HTTP_CODE"
  if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "202" ]; then
    echo "ERROR: Expected 200/202 from $SERVICE_URL but got $HTTP_CODE" >&2
    exit 1
  fi

  echo "--- Run stdio smoke test ---"
  bash "$WORKDIR/mcp/testing/filesystem-smoke.sh"

  echo "=== Deployment complete ==="
} | tee "$LOG_FILE"

echo "Log saved to $LOG_FILE"
