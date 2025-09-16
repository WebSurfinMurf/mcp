#!/usr/bin/env python3
"""
Generate MCP configuration for Claude Code
Creates individual MCP server entries that work with stdio
"""

import json
from tool_definitions import TOOL_DEFINITIONS

def generate_mcp_config():
    """Generate MCP configuration for Claude Code with working stdio commands"""
    
    config = {
        "mcpServers": {}
    }
    
    # Add filesystem MCP
    config["mcpServers"]["mcp-filesystem"] = {
        "command": "docker",
        "args": [
            "run", "--rm", "-i",
            "-v", "/home/administrator:/workspace:rw",
            "mcp/filesystem"
        ]
    }
    
    # Add postgres MCP  
    config["mcpServers"]["mcp-postgres"] = {
        "command": "docker",
        "args": [
            "run", "--rm", "-i",
            "--network", "postgres-net",
            "-e", "DATABASE_URI=postgresql://admin:Pass123qp@postgres:5432/postgres",
            "crystaldba/postgres-mcp"
        ]
    }
    
    # Add GitHub MCP (using npx)
    config["mcpServers"]["mcp-github"] = {
        "command": "npx",
        "args": ["@modelcontextprotocol/server-github"],
        "env": {
            "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
        }
    }
    
    # These services require persistent connections via SSE proxy
    # and don't work well with direct stdio
    services_via_proxy = ["monitoring", "n8n", "playwright", "timescaledb"]
    
    return config

def main():
    config = generate_mcp_config()
    
    # Save to file
    with open("/home/administrator/.config/claude/mcp_servers_working.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print("Generated MCP configuration with working services:")
    print(json.dumps(config, indent=2))
    print("\nConfiguration saved to: /home/administrator/.config/claude/mcp_servers_working.json")
    print("\nTo use this configuration:")
    print("1. Backup current config: cp ~/.config/claude/mcp_servers.json ~/.config/claude/mcp_servers.json.bak")
    print("2. Apply new config: cp ~/.config/claude/mcp_servers_working.json ~/.config/claude/mcp_servers.json")
    print("3. Restart Claude Code")

if __name__ == "__main__":
    main()