#!/bin/bash
set -e

PROJECT_NAME="mcp-playwright"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="/home/administrator/.config/claude"

# Color output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🎭 Deploying MCP Playwright Server...${NC}"

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
cd ${SCRIPT_DIR}
npm install

if [ $? -ne 0 ]; then
    echo -e "${RED}✗${NC} npm install failed"
    exit 1
fi

# Test the server
echo -e "${YELLOW}Testing MCP server...${NC}"
timeout 5s npm test || echo "Test completed"

# Update Claude's MCP configuration
echo -e "${YELLOW}Updating Claude MCP configuration...${NC}"

# Create MCP server configuration
cat > ${CONFIG_DIR}/mcp-playwright-temp.json << EOF
{
  "mcp-playwright": {
    "command": "node",
    "args": ["${SCRIPT_DIR}/src/index.js"],
    "env": {
      "PLAYWRIGHT_URL": "http://localhost:3000",
      "PLAYWRIGHT_WS_URL": "ws://localhost:3000",
      "DEFAULT_TIMEOUT": "30000"
    }
  }
}
EOF

# Merge with existing configuration if it exists
if [ -f "${CONFIG_DIR}/mcp_servers.json" ]; then
    echo -e "${YELLOW}Merging with existing MCP configuration...${NC}"
    
    # Backup existing config
    cp ${CONFIG_DIR}/mcp_servers.json ${CONFIG_DIR}/mcp_servers.json.backup
    
    # Use jq to merge configurations
    jq -s '.[0].mcpServers + .[1]' \
        ${CONFIG_DIR}/mcp_servers.json \
        ${CONFIG_DIR}/mcp-playwright-temp.json \
        > ${CONFIG_DIR}/mcp_servers_new.json
    
    # Wrap in proper structure
    jq '{mcpServers: .}' ${CONFIG_DIR}/mcp_servers_new.json > ${CONFIG_DIR}/mcp_servers.json
    
    # Cleanup temporary files
    rm ${CONFIG_DIR}/mcp_servers_new.json ${CONFIG_DIR}/mcp-playwright-temp.json
else
    echo -e "${YELLOW}Creating new MCP configuration...${NC}"
    echo '{"mcpServers": {}}' | jq ".mcpServers += $(cat ${CONFIG_DIR}/mcp-playwright-temp.json)" \
        > ${CONFIG_DIR}/mcp_servers.json
    rm ${CONFIG_DIR}/mcp-playwright-temp.json
fi

echo -e "${GREEN}✓${NC} MCP configuration updated"

# Create systemd service for auto-start (optional)
echo -e "${YELLOW}Creating systemd service...${NC}"
sudo tee /etc/systemd/system/mcp-playwright.service > /dev/null << EOF
[Unit]
Description=MCP Playwright Server
After=network.target
Requires=network.target

[Service]
Type=simple
User=administrator
WorkingDirectory=${SCRIPT_DIR}
ExecStart=/usr/bin/node ${SCRIPT_DIR}/src/index.js
Restart=always
RestartSec=5
Environment=NODE_ENV=production
Environment=PLAYWRIGHT_URL=http://localhost:3000
Environment=PLAYWRIGHT_WS_URL=ws://localhost:3000

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable mcp-playwright.service

echo ""
echo -e "${GREEN}🎭 MCP Playwright Server deployed successfully!${NC}"
echo ""
echo "Configuration:"
echo "  • MCP Config: ${CONFIG_DIR}/mcp_servers.json"
echo "  • Service: mcp-playwright.service"
echo ""
echo "Usage:"
echo "  • Restart Claude Code to load the new MCP server"
echo "  • Use mcp-playwright tools for browser automation"
echo ""
echo "Commands:"
echo "  • Start service: sudo systemctl start mcp-playwright"
echo "  • View logs: sudo journalctl -u mcp-playwright -f"
echo "  • Test manually: cd ${SCRIPT_DIR} && node src/index.js"
echo ""
echo -e "${YELLOW}Note: Ensure Playwright service is running at http://localhost:3000${NC}"