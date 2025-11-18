#!/bin/bash
set -euo pipefail

TARGET_KEY="filesystem"
FILE_LIST=(
  /home/administrator/projects/.claude/mcp.json
  /home/administrator/.config/claude/mcp-settings.json
  /home/administrator/.config/claude/mcp-servers.json
)

for file in "${FILE_LIST[@]}"; do
  if [[ -f "$file" ]]; then
    tmp="$(mktemp)"
    if jq "del(.mcpServers.\"$TARGET_KEY\")" "$file" > "$tmp" 2>/dev/null; then
      mv "$tmp" "$file"
      echo "Removed $TARGET_KEY from $file"
    else
      rm -f "$tmp"
      echo "Skipped $file (not JSON or lacks mcpServers)"
    fi
  fi

done

echo "Reset complete."
