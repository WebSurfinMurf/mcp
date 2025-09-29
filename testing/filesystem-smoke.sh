#!/bin/bash
set -euo pipefail

WORKDIR="/home/administrator/projects"

echo "--- stdio bridge initialize ---"
cd "$WORKDIR/mcp/filesystem"
echo '{"jsonrpc":"2.0","method":"initialize","id":1}' | python3 mcp-bridge.py

echo "--- Claude CLI tool smoke test ---"
HOME="$WORKDIR" claude -p "Use filesystem to list the contents of the /workspace directory"
