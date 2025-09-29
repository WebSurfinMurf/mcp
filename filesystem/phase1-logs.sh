#!/bin/bash
set -euo pipefail

WORKDIR="/home/administrator/projects"
LOG_DIR="$WORKDIR/mcp/logs"
LOG_FILE="$LOG_DIR/filesystem-phase1-docker-$(date +%Y%m%d-%H%M%S).log"

mkdir -p "$LOG_DIR"

{
  echo "=== mcp-filesystem logs since last run ==="
  date
  echo
  docker-compose logs --tail 200
} | tee "$LOG_FILE"

echo "Log saved to $LOG_FILE"
