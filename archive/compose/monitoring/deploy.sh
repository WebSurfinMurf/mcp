#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== MCP Monitoring Server Deployment ===${NC}"

PROJECT_DIR="/home/administrator/projects/mcp-monitoring"
CONFIG_DIR="/home/administrator/.config/claude"

# Install dependencies
echo "Installing dependencies..."
cd ${PROJECT_DIR}
npm install

# Test the server
echo ""
echo "Testing MCP server..."
npm test

# Update Claude's MCP configuration
echo ""
echo "Updating Claude MCP configuration..."

# Create temporary config for this server
cat > ${CONFIG_DIR}/mcp-monitoring-config.json << EOF
{
  "monitoring": {
    "command": "node",
    "args": ["${PROJECT_DIR}/src/index.js"],
    "env": {
      "LOKI_URL": "http://localhost:3100",
      "NETDATA_URL": "http://localhost:19999",
      "DEFAULT_LIMIT": "100",
      "DEFAULT_HOURS": "24"
    }
  }
}
EOF

# Check if mcp_servers.json exists
if [ -f "${CONFIG_DIR}/mcp_servers.json" ]; then
  echo "Merging with existing MCP configuration..."
  # Create backup
  cp ${CONFIG_DIR}/mcp_servers.json ${CONFIG_DIR}/mcp_servers.json.bak
  
  # Merge configurations
  jq -s '.[0] * {mcpServers: (.[0].mcpServers + .[1])}' \
    ${CONFIG_DIR}/mcp_servers.json \
    ${CONFIG_DIR}/mcp-monitoring-config.json \
    > ${CONFIG_DIR}/mcp_servers.json.tmp
  mv ${CONFIG_DIR}/mcp_servers.json.tmp ${CONFIG_DIR}/mcp_servers.json
else
  echo "Creating new MCP configuration..."
  echo '{"mcpServers": {}}' | jq ".mcpServers += \$(cat ${CONFIG_DIR}/mcp-monitoring-config.json)" \
    > ${CONFIG_DIR}/mcp_servers.json
fi

# Clean up temp file
rm ${CONFIG_DIR}/mcp-monitoring-config.json

echo -e "${GREEN}✓ MCP Monitoring server deployed successfully${NC}"
echo ""
echo "Next steps:"
echo "1. Restart Claude Code to load the new MCP server"
echo "2. Test with: search_logs tool with query {job=\"containerlogs\"}"
echo ""
echo "Available tools:"
echo "  - search_logs: Query logs with LogQL"
echo "  - get_recent_errors: Find recent errors"
echo "  - get_container_logs: Get specific container logs"
echo "  - get_system_metrics: Get system metrics"
echo "  - check_service_health: Check service health"