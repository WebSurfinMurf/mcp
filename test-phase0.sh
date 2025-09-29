#!/bin/bash
set -euo pipefail

WORKDIR="/home/administrator/projects"
LOG_DIR="$WORKDIR/mcp/logs"
LOG_FILE="$LOG_DIR/phase0-baseline-$(date +%Y%m%d-%H%M%S).log"

mkdir -p "$LOG_DIR"

{
  echo "=== Phase 0 Baseline Smoke Tests ==="
  date
  echo

  echo "--- Docker Containers (expect mcp-filesystem running) ---"
  docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'mcp-filesystem|NAME'
  echo

  echo "--- /health endpoint ---"
  curl -sf http://localhost:9073/health | jq .
  echo

  echo "--- SSE HEADERS (curl --head) ---"
  curl -sI http://localhost:9073/sse | sed -n '1,10p'
  echo

  echo "--- stdio bridge initialize ---"
  cd "$WORKDIR/mcp/filesystem"
  echo '{"jsonrpc": "2.0", "method": "initialize", "id": 1}' | python3 mcp-bridge.py
  echo

  echo "--- stdio bridge list_files ---"
  echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"list_files","arguments":{"path":"."}},"id":2}' | python3 mcp-bridge.py | jq .
  echo

  echo "=== End Phase 0 Baseline ==="
} | tee "$LOG_FILE"

echo "Log saved to $LOG_FILE"
