#!/bin/bash
# Setup script for Claude Code CLI integration

set -e

echo "=== MCP Code Executor - Claude CLI Setup ==="
echo

# Check if container is running
echo "1. Checking container status..."
if docker ps --filter name=mcp-code-executor --format '{{.Names}}' | grep -q mcp-code-executor; then
    echo "✅ Container is running"
else
    echo "❌ Container not running. Starting..."
    cd /home/administrator/projects/mcp/code-executor
    docker compose up -d
    sleep 2
fi

# Fix permissions
echo
echo "2. Fixing permissions..."
docker exec -u root mcp-code-executor chown -R node:node /workspace /tmp/executions
echo "✅ Permissions fixed"

# Install MCP SDK
echo
echo "3. Installing MCP SDK..."
docker exec mcp-code-executor npm install @modelcontextprotocol/sdk 2>&1 | grep -v "npm WARN" || true
echo "✅ MCP SDK installed"

# Copy files to container
echo
echo "4. Copying integration files..."
docker cp /home/administrator/projects/mcp/code-executor/mcp-server.ts mcp-code-executor:/app/mcp-server.ts
docker cp /home/administrator/projects/mcp/code-executor/package.json mcp-code-executor:/app/package.json
echo "✅ Files copied"

# Generate wrappers
echo
echo "5. Generating tool wrappers..."
docker exec mcp-code-executor npm run generate-wrappers
echo "✅ Wrappers generated"

# Test health
echo
echo "6. Testing API health..."
curl -s http://localhost:9091/health | jq -r '"✅ API healthy - \(.servers) servers, \(.totalTools) tools"'

# Check MCP config
echo
echo "7. Checking Claude Code MCP configuration..."
if [ -f "$HOME/projects/.claude/mcp.json" ]; then
    if grep -q "code-executor" "$HOME/projects/.claude/mcp.json"; then
        echo "✅ code-executor already configured in $HOME/projects/.claude/mcp.json"
    else
        echo "⚠️  code-executor NOT found in $HOME/projects/.claude/mcp.json"
        echo
        echo "Add this to your $HOME/projects/.claude/mcp.json:"
        echo
        cat /home/administrator/projects/mcp/code-executor/claude-mcp-config.json
        echo
    fi
else
    echo "⚠️  $HOME/projects/.claude/mcp.json does not exist"
    echo
    echo "Create $HOME/projects/.claude/mcp.json with:"
    echo
    cat /home/administrator/projects/mcp/code-executor/claude-mcp-config.json
    echo
fi

echo
echo "=== Setup Complete ==="
echo
echo "Next steps:"
echo "1. Exit Claude Code CLI"
echo "2. Ensure $HOME/projects/.claude/mcp.json includes code-executor config (shown above if needed)"
echo "3. Restart Claude Code CLI"
echo "4. Test with: 'List available MCP servers'"
echo
