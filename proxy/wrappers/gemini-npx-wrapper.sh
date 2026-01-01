#!/bin/bash
# Wrapper for Gemini Image MCP server (npx version)
# Loads secrets from env file and runs npx mcp-image
set -e

# Load secrets
if [ -f /secrets/mcp-gemini-image.env ]; then
    set -a
    source /secrets/mcp-gemini-image.env
    set +a
fi

export NODE_NO_WARNINGS=1
export GEMINI_API_KEY="${GEMINI_API_KEY}"
export IMAGE_OUTPUT_DIR="${IMAGE_OUTPUT_DIR:-/generated-images}"

exec npx -y mcp-image
