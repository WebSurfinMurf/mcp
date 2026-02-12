#!/bin/bash
# Host-side MCP wrapper — detects user group, reads API key, docker execs into container
# Both admin and developer users point to this same script in their ~/.claude.json

SECRETS_DIR="/home/administrator/projects/secrets"

# Determine API key: prefer env var, fall back to group-based key file
if [ -n "$CODE_EXECUTOR_API_KEY" ]; then
    API_KEY="$CODE_EXECUTOR_API_KEY"
elif id -Gn 2>/dev/null | grep -qw administrators; then
    API_KEY=$(cat "${SECRETS_DIR}/code-executor-admin.key" 2>/dev/null)
elif id -Gn 2>/dev/null | grep -qw developers; then
    API_KEY=$(cat "${SECRETS_DIR}/code-executor-developer.key" 2>/dev/null)
else
    API_KEY=""
fi

exec docker exec -i \
    -e "CODE_EXECUTOR_API_KEY=${API_KEY}" \
    -e "CODE_EXECUTOR_URL=http://localhost:3000" \
    mcp-code-executor \
    npx tsx /app/mcp-server.ts
