#!/bin/bash
set -euo pipefail

WORKDIR="/home/administrator/projects"
SERVICE_DIR="$WORKDIR/mcp/filesystem"
LOG_DIR="$WORKDIR/mcp/logs"
LOG_FILE="$LOG_DIR/filesystem-phase1-$(date +%Y%m%d-%H%M%S).log"

mkdir -p "$LOG_DIR"

{
  echo "=== Phase 1 – mcp-filesystem Redeploy & Validation ==="
  date
  echo

  echo "--- Redeploy container ---"
  cd "$SERVICE_DIR"
  ./deploy.sh
  echo

  echo "--- Container status ---"
  docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'mcp-filesystem|NAME'
  echo

  echo "--- /health endpoint ---"
  curl -sf http://localhost:9073/health | jq .
  echo

  echo "--- SSE probe (5s timeout) ---"
  curl -s -S -i -H 'Accept: text/event-stream' --max-time 5 http://localhost:9073/sse | sed -n '1,10p'
  echo

  echo "--- stdio bridge initialize ---"
  echo '{"jsonrpc": "2.0", "method": "initialize", "id": 1}' | python3 mcp-bridge.py
  echo

  echo "--- stdio bridge list_files ---"
  echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"list_files","arguments":{"path":"."}},"id":2}' | python3 mcp-bridge.py | jq .
  echo

  echo "=== End Phase 1 Validation ==="
} | tee "$LOG_FILE"

echo "Log saved to $LOG_FILE"
