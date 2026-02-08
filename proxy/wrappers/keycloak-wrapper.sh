#!/bin/bash
# MCP Keycloak Server Wrapper
# Loads secrets and starts the MCP Keycloak server
#
# This wrapper is used by the MCP Proxy to start the Keycloak MCP server
# with proper environment variables loaded from the secrets file.

set -e

# Load Keycloak admin credentials from secrets
SECRETS_FILE="/secrets/keycloak-admin.env"

if [[ -f "$SECRETS_FILE" ]]; then
    set -a
    source "$SECRETS_FILE"
    set +a
else
    echo "Error: Secrets file not found: $SECRETS_FILE" >&2
    exit 1
fi

# Verify required environment variables
if [[ -z "$KEYCLOAK_URL" ]] || [[ -z "$KEYCLOAK_REALM" ]] || \
   [[ -z "$KEYCLOAK_ADMIN_USERNAME" ]] || [[ -z "$KEYCLOAK_ADMIN_PASSWORD" ]]; then
    echo "Error: Missing required environment variables" >&2
    echo "Required: KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_ADMIN_USERNAME, KEYCLOAK_ADMIN_PASSWORD" >&2
    exit 1
fi

# Start the MCP Keycloak server
exec node /workspace/mcp/keycloak/dist/index.js
