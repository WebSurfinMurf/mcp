#!/bin/bash

# MCP TimescaleDB Server - STDIO deployment for Claude integration

# Load environment variables from .env file if it exists
if [ -f /home/administrator/projects/mcp-timescaledb/.env ]; then
    source /home/administrator/projects/mcp-timescaledb/.env
fi

# Verify required environment variables are set
if [ -z "$TSDB_PASSWORD" ]; then
    echo "Error: TSDB_PASSWORD environment variable is not set"
    exit 1
fi

# Navigate to project directory
cd /home/administrator/projects/mcp-timescaledb

# Install dependencies if needed
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Run the server in stdio mode
exec python server.py