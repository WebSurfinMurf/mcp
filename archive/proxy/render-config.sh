#!/usr/bin/env bash
set -euo pipefail

# Generates config/config.json from config/config.template.json by
# injecting MCP_PROXY_TOKEN from the environment (or secrets file).
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CONFIG_DIR="${ROOT_DIR}/config"
TEMPLATE="${CONFIG_DIR}/config.template.json"
OUTPUT="${CONFIG_DIR}/config.json"
DEFAULT_ENV_FILE="$HOME/projects/secrets/mcp-proxy.env"
ENV_FILE="${ENV_FILE:-${DEFAULT_ENV_FILE}}"

if [[ ! -f "${TEMPLATE}" ]]; then
  echo "Template not found: ${TEMPLATE}" >&2
  exit 1
fi

if [[ -z "${MCP_PROXY_TOKEN:-}" ]]; then
  if [[ -f "${ENV_FILE}" ]]; then
    # shellcheck disable=SC1090
    set -a
    source "${ENV_FILE}"
    set +a
  fi
fi

if [[ -z "${MCP_PROXY_TOKEN:-}" ]]; then
  cat <<ERR >&2
MCP_PROXY_TOKEN is not set.
Either export MCP_PROXY_TOKEN or create ${ENV_FILE} with:
  MCP_PROXY_TOKEN=your-token-here
ERR
  exit 1
fi

TEMPLATE="${TEMPLATE}" OUTPUT="${OUTPUT}" \
python3 - <<'PY'
import json
import os

template_path = os.environ["TEMPLATE"]
output_path = os.environ["OUTPUT"]
token = os.environ["MCP_PROXY_TOKEN"]

with open(template_path, "r", encoding="utf-8") as f:
    data = json.load(f)

if os.path.exists(output_path):
    with open(output_path, "r", encoding="utf-8") as f:
        current = json.load(f)
    if isinstance(current, dict) and current.get("mcpServers"):
        data["mcpServers"] = current["mcpServers"]

options = data.setdefault("mcpProxy", {}).setdefault("options", {})
options["authTokens"] = [token]

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY

chmod 600 "${OUTPUT}"
echo "Wrote ${OUTPUT}" >&2
