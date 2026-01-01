#!/bin/bash
# Wrapper for ArangoDB MCP server
# Loads secrets from env file and runs npx arango-server
set -e

# Load secrets
if [ -f /secrets/mcp-arangodb.env ]; then
    set -a
    source /secrets/mcp-arangodb.env
    set +a
fi

# Map env var names to what arango-server expects
export ARANGO_URL="${ARANGODB_URL:-http://arangodb:8529}"
export ARANGO_DB="${ARANGODB_DATABASE:-ai_memory}"
export ARANGO_USERNAME="${ARANGODB_USERNAME:-root}"
export ARANGO_PASSWORD="${ARANGODB_PASSWORD}"
export NODE_NO_WARNINGS=1

exec npx -y arango-server
