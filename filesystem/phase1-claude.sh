#!/bin/bash
set -euo pipefail

WORKDIR="/home/administrator/projects"
LOG_DIR="$WORKDIR/mcp/logs"
LOG_FILE="$LOG_DIR/filesystem-phase1-claude-$(date +%Y%m%d-%H%M%S).log"

mkdir -p "$LOG_DIR"


CLAUDE_HOME="/home/administrator/projects"

run_claude() {
  HOME="$CLAUDE_HOME" claude "$@"
}

{
  echo "=== Phase 1 – mcp-filesystem Claude CLI Registration ==="
  date
  echo

  echo "--- Remove existing registration (ignore errors) ---"
  run_claude mcp remove filesystem --scope user || true
  run_claude mcp remove filesystem || true
  echo

  echo "--- Add SSE registration ---"
  run_claude mcp add filesystem http://localhost:9073/sse --transport sse
  echo

  echo "--- Current MCP registrations ---"
  run_claude mcp list
  echo

  echo "=== End Claude CLI Registration ==="
} | tee "$LOG_FILE"

echo "Log saved to $LOG_FILE"
