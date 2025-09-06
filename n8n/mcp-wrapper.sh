#!/bin/bash
# Wrapper script to load n8n MCP environment variables

# Load environment variables from secrets
if [ -f "/home/administrator/secrets/n8n-mcp.env" ]; then
    source /home/administrator/secrets/n8n-mcp.env
    export N8N_URL
    export N8N_API_KEY
fi

# Execute the MCP server
exec node /home/administrator/projects/mcp/n8n/src/index.js "$@"
