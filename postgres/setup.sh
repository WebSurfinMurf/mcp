#!/bin/bash
# Setup script for postgres-mcp stdio mode

set -euo pipefail

echo "Installing postgres-mcp for stdio mode..."

# Install postgres-mcp package
pip3 install --user postgres-mcp>=0.3.0

echo "✅ postgres-mcp installed successfully"
echo ""
echo "To register with Codex CLI:"
echo "codex mcp add postgres-stdio python3 /home/administrator/projects/mcp/postgres/postgres-mcp-stdio.py"
echo ""
echo "To test directly:"
echo "echo '{\"jsonrpc\":\"2.0\",\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{},\"clientInfo\":{\"name\":\"test\",\"version\":\"1.0.0\"}},\"id\":1}' | python3 /home/administrator/projects/mcp/postgres/postgres-mcp-stdio.py"