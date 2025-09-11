#!/bin/bash
# Wrapper script to load n8n MCP environment variables

# Load environment variables from secrets (standardized naming)
if [ -f "/home/administrator/secrets/mcp-n8n.env" ]; then
    source /home/administrator/secrets/mcp-n8n.env
    export N8N_URL
    export N8N_API_KEY
elif [ -f "/home/administrator/secrets/n8n-mcp.env" ]; then
    # Fallback to old location for compatibility
    source /home/administrator/secrets/n8n-mcp.env
    export N8N_URL
    export N8N_API_KEY
fi

# Execute the MCP server
exec node /home/administrator/projects/mcp/n8n/src/index.js "$@"
