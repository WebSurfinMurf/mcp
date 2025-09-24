#!/usr/bin/env bash
set -euo pipefail

# list-central.sh
# List current mcpServers entries from the central proxy config in
# table, names-only, or raw JSON form.
#
# Defaults:
#   PROXY_DIR=/home/administrator/projects/mcp/proxy
#   CONFIG=$PROXY_DIR/config/config.json
#
# Requires: jq (preferred) OR python3 (fallback)

PROXY_DIR="/home/administrator/projects/mcp/proxy"
CONFIG="${PROXY_DIR}/config/config.json"
FORMAT="table"   # table|names|json

usage() {
  cat <<EOF
Usage:
  $0 [--format table|names|json] [--config <path>]

Examples:
  $0 --format table | column -t
  $0 --format names
  $0 --format json
EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --format) FORMAT="${2:-}"; shift 2 ;;
    --config) CONFIG="${2:-}"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1" >&2; usage ;;
  esac
done

[[ -f "$CONFIG" ]] || { echo "Config not found: $CONFIG" >&2; exit 1; }

if command -v jq >/dev/null 2>&1; then
  case "$FORMAT" in
    json)
      jq -r '.mcpServers // {}' "$CONFIG"
      ;;
    names)
      jq -r '(.mcpServers // {}) | keys[]' "$CONFIG"
      ;;
    table|*)
      jq -r '
        (.mcpServers // {}) as $m
        | if ($m|length)==0 then
            "SERVICE\tURL\tAUTH_HEADER"
          else
            (["SERVICE","URL","AUTH_HEADER"]),
            ($m | to_entries[] | [
              .key,
              (.value.url // "-"),
              (.value.headers.Authorization // "-")
            ])
          end
        | @tsv
      ' "$CONFIG"
      ;;
  esac
else
  python3 - <<PY
import json,sys
fmt="${FORMAT}"
cfg=json.load(open("${CONFIG}","r",encoding="utf-8"))
m=cfg.get("mcpServers") or {}
if fmt=="json":
    print(json.dumps(m, indent=2, ensure_ascii=False))
elif fmt=="names":
    for k in m.keys(): print(k)
else:
    print("SERVICE\tURL\tAUTH_HEADER")
    for k,v in m.items():
        url=v.get("url","-")
        auth=(v.get("headers") or {}).get("Authorization","-")
        print(f"{k}\t{url}\t{auth}")
PY
fi