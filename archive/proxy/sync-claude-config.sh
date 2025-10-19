#!/usr/bin/env bash
set -euo pipefail

# sync-claude-config.sh
# Generate a ~/.config/claude/mcp-settings.json file that points the Claude CLI
# at the central MCP proxy running on linuxserver.lan.
#
# Usage:
#   ./sync-claude-config.sh [path-to-env]
#
# The script loads MCP_PROXY_TOKEN from the secrets file (default:
# $HOME/projects/secrets/mcp-proxy.env) and writes a minimal MCP config
# containing the postgres and fetch proxy entries.

DEFAULT_ENV="$HOME/projects/secrets/mcp-proxy.env"
ENV_FILE="${1:-$DEFAULT_ENV}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Secrets file not found: $ENV_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

if [[ -z "${MCP_PROXY_TOKEN:-}" ]]; then
  echo "MCP_PROXY_TOKEN is not defined in $ENV_FILE" >&2
  exit 1
fi

CONFIG_DIR="$HOME/.config/claude"
CONFIG_FILE="$CONFIG_DIR/mcp-settings.json"
mkdir -p "$CONFIG_DIR"

if [[ -f "$CONFIG_FILE" ]]; then
  cp "$CONFIG_FILE" "${CONFIG_FILE}.bak-$(date +%Y%m%d-%H%M%S)"
fi

cat > "$CONFIG_FILE" <<EOF_JSON
{
  "mcpServers": {
    "postgres-proxy": {
      "type": "sse",
      "url": "http://linuxserver.lan:9090/postgres/sse",
      "headers": {
        "Authorization": "Bearer ${MCP_PROXY_TOKEN}"
      }
    },
    "fetch-proxy": {
      "type": "sse",
      "url": "http://linuxserver.lan:9090/fetch/sse",
      "headers": {
        "Authorization": "Bearer ${MCP_PROXY_TOKEN}"
      }
    }
  }
}
EOF_JSON

chmod 600 "$CONFIG_FILE"
echo "Updated $CONFIG_FILE" >&2
