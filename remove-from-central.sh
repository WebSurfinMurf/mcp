#!/usr/bin/env bash
set -euo pipefail

# remove-from-central.sh
# Safely remove an mcpServers entry from the central proxy config,
# restart the central proxy, and (optionally) verify the route is gone.
#
# Defaults:
#   PROXY_DIR=/home/administrator/projects/mcp/proxy
#   CONFIG=$PROXY_DIR/config/config.json
#   CENTRAL_HOST=linuxserver.lan
#   CENTRAL_PORT=9090
#
# Requires: jq (preferred) OR python3 (fallback)

PROXY_DIR="/home/administrator/projects/mcp/proxy"
CONFIG="${PROXY_DIR}/config/config.json"
CENTRAL_HOST="linuxserver.lan"
CENTRAL_PORT="9090"

SERVICE=""
DRY_RUN=0
SKIP_RESTART=0
RUN_TEST=0

usage() {
  cat <<EOF
Usage:
  $0 --service <name> [--dry-run] [--skip-restart] [--test]
     [--config <path>] [--host <linuxserver.lan>] [--central-port <9090>]

Examples:
  $0 --service filesystem --test
  $0 --service fetch --skip-restart --dry-run
EOF
  exit 1
}

err() { printf "\033[31mERROR:\033[0m %s\n" "$*" >&2; }
info(){ printf "\033[36mINFO:\033[0m %s\n" "$*"; }
ok()  { printf "\033[32mOK:\033[0m %s\n" "$*"; }

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --service) SERVICE="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --skip-restart) SKIP_RESTART=1; shift ;;
    --test) RUN_TEST=1; shift ;;
    --config) CONFIG="${2:-}"; shift 2 ;;
    --host) CENTRAL_HOST="${2:-}"; shift 2 ;;
    --central-port) CENTRAL_PORT="${2:-}"; shift 2 ;;
    -h|--help) usage ;;
    *) err "Unknown option: $1"; usage ;;
  esac
done

[[ -z "$SERVICE" ]] && err "--service is required" && usage
[[ -f "$CONFIG" ]] || { err "Config not found: $CONFIG"; exit 1; }

info "Central config: $CONFIG"
info "Removing service: $SERVICE"
[[ $DRY_RUN -eq 1 ]] && info "DRY RUN (no write/restart)"

# Verify existence
EXISTS="false"
if command -v jq >/dev/null 2>&1; then
  EXISTS=$(jq -r --arg name "$SERVICE" '(.mcpServers // {}) | has($name)' "$CONFIG")
else
  EXISTS=$(python3 - <<PY
import json; import sys
cfg=json.load(open("$CONFIG","r",encoding="utf-8"))
print("true" if isinstance(cfg.get("mcpServers"),dict) and "$SERVICE" in cfg["mcpServers"] else "false")
PY
)
fi

if [[ "$EXISTS" != "true" ]]; then
  info "Service '$SERVICE' not present—nothing to do."
  exit 0
fi

# Backup
STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP="${CONFIG}.bak-${STAMP}"
cp -a "$CONFIG" "$BACKUP"
ok "Backup created: $BACKUP"

TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT

# Remove entry
if command -v jq >/dev/null 2>&1; then
  jq --arg name "$SERVICE" '
    . as $root
    | (if has("mcpServers") then . else . + {"mcpServers":{}} end)
    | del(.mcpServers[$name])
  ' "$CONFIG" > "$TMP"
else
  python3 - "$CONFIG" "$SERVICE" > "$TMP" <<'PY'
import json,sys
cfg_path, name = sys.argv[1], sys.argv[2]
with open(cfg_path,"r",encoding="utf-8") as f:
    data=json.load(f)
m=data.get("mcpServers") or {}
if isinstance(m,dict) and name in m:
    del m[name]
data["mcpServers"]=m
print(json.dumps(data, indent=2, ensure_ascii=False))
PY
fi

# Validate JSON
if command -v jq >/dev/null 2>&1; then
  jq -e . "$TMP" >/dev/null
else
  python3 - <<PY >/dev/null
import json; json.load(open("$TMP","r",encoding="utf-8"))
PY
fi
ok "Config JSON validated."

# Write (unless dry)
if [[ $DRY_RUN -eq 1 ]]; then
  info "Dry-run output left in: $TMP"
  exit 0
fi
mv "$TMP" "$CONFIG"
ok "Config updated."

# Restart central and health check
if [[ $SKIP_RESTART -eq 1 ]]; then
  info "Skipping restart per --skip-restart"
else
  (cd "$PROXY_DIR" && docker compose restart mcp-proxy)
  ok "Central proxy restarted."
  curl -fsS "http://${CENTRAL_HOST}:${CENTRAL_PORT}/" >/dev/null
  ok "Central proxy health check passed."
fi

# Optional negative test (should fail/close)
if [[ $RUN_TEST -eq 1 ]]; then
  info "Verifying route is removed (expect failure or non-2xx)…"
  set +e
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H 'Accept: text/event-stream' \
    "http://${CENTRAL_HOST}:${CENTRAL_PORT}/${SERVICE}/sse")
  set -e
  if [[ "$HTTP_CODE" == "404" || "$HTTP_CODE" == "401" || "$HTTP_CODE" == "403" || "$HTTP_CODE" == "000" ]]; then
    ok "Route removed (HTTP $HTTP_CODE)."
  else
    err "Unexpected HTTP $HTTP_CODE from removed route—check central logs."
    exit 1
  fi
fi