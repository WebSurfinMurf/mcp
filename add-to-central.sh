#!/usr/bin/env bash
set -euo pipefail

# add-to-central.sh
# Safely add/update a bridge URL under mcpServers in the central proxy config,
# then restart the central proxy and optionally test the new SSE path.
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
URL=""
PORT=""
HEADERS_JSON="{}"
ADD_AUTH=0
DRY_RUN=0
FORCE=0
SKIP_RESTART=0
RUN_TEST=0
TEST_TOKEN="" # override for central test request Authorization

usage() {
  cat <<EOF
Usage:
  $0 --service <name> [--url <http://mcp-<service>-bridge:<port>/<service>/sse> | --port <port>]
     [--headers '{"X-Env":"prod"}'] [--add-auth] [--dry-run] [--force]
     [--skip-restart] [--test] [--test-token <token>]
     [--config <path>] [--host <linuxserver.lan>] [--central-port <9090>]

Examples:
  # Typical bridge URL (internal Docker DNS):
  $0 --service filesystem --port 9071 --add-auth
  $0 --service fetch --url http://mcp-fetch-bridge:9072/fetch/sse --add-auth

Notes:
  --add-auth adds {"Authorization": "Bearer \${MCP_PROXY_TOKEN}"} to headers.
  --force overwrites existing entry for the service.
  --test performs an SSE smoke test on http://<host>:<port>/<service>/sse
EOF
  exit 1
}

# Small helpers
err() { printf "\033[31mERROR:\033[0m %s\n" "$*" >&2; }
info(){ printf "\033[36mINFO:\033[0m %s\n" "$*"; }
ok()  { printf "\033[32mOK:\033[0m %s\n" "$*"; }

# Arg parse
while [[ $# -gt 0 ]]; do
  case "$1" in
    --service) SERVICE="${2:-}"; shift 2 ;;
    --url) URL="${2:-}"; shift 2 ;;
    --port) PORT="${2:-}"; shift 2 ;;
    --headers) HEADERS_JSON="${2:-}"; shift 2 ;;
    --add-auth) ADD_AUTH=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --force) FORCE=1; shift ;;
    --skip-restart) SKIP_RESTART=1; shift ;;
    --test) RUN_TEST=1; shift ;;
    --test-token) TEST_TOKEN="${2:-}"; shift 2 ;;
    --config) CONFIG="${2:-}"; shift 2 ;;
    --host) CENTRAL_HOST="${2:-}"; shift 2 ;;
    --central-port) CENTRAL_PORT="${2:-}"; shift 2 ;;
    -h|--help) usage ;;
    *) err "Unknown option: $1"; usage ;;
  esac
done

[[ -z "$SERVICE" ]] && err "--service is required" && usage
if [[ -z "${URL}" && -z "${PORT}" ]]; then
  err "Either --url or --port is required"; usage
fi
if [[ -z "${URL}" && -n "${PORT}" ]]; then
  URL="http://mcp-${SERVICE}-bridge:${PORT}/${SERVICE}/sse"
fi

# Validate headers JSON early (with jq if present, else python)
if command -v jq >/dev/null 2>&1; then
  if ! echo "$HEADERS_JSON" | jq -e . >/dev/null 2>&1; then
    err "--headers is not valid JSON"; exit 1
  fi
else
  python3 - <<PY 2>/dev/null || { err "--headers is not valid JSON"; exit 1; }
import json,sys
json.loads("""$HEADERS_JSON""")
PY
fi

# Merge Authorization header if requested
if [[ $ADD_AUTH -eq 1 ]]; then
  TOKEN="${MCP_PROXY_TOKEN:-}"
  [[ -z "$TOKEN" ]] && { err "--add-auth set, but MCP_PROXY_TOKEN env is empty"; exit 1; }
  if command -v jq >/dev/null 2>&1; then
    HEADERS_JSON=$(jq -nc --argjson base "$HEADERS_JSON" --arg v "Bearer $TOKEN" '
      ($base|type=="object") as $ok
      | (if $ok then $base else {} end) + {"Authorization": $v}
    ')
  else
    HEADERS_JSON=$(python3 - <<PY
import json
base = json.loads("""$HEADERS_JSON""") if """$HEADERS_JSON""" else {}
if not isinstance(base, dict): base = {}
base["Authorization"] = "Bearer ${TOKEN}"
print(json.dumps(base))
PY
)
  fi
fi

# Compose the service object
SERVICE_OBJ=''
if command -v jq >/dev/null 2>&1; then
  SERVICE_OBJ=$(jq -nc --arg url "$URL" --argjson headers "$HEADERS_JSON" '
    if ($headers|length)>0 then {"url":$url,"headers":$headers} else {"url":$url} end
  ')
else
  SERVICE_OBJ=$(python3 - <<PY
import json
h = json.loads("""$HEADERS_JSON""") if """$HEADERS_JSON""" else {}
obj = {"url": "$URL"}
if isinstance(h, dict) and h:
    obj["headers"] = h
print(json.dumps(obj))
PY
)
fi

# Show intent
info "Central config: $CONFIG"
info "Service: $SERVICE"
info "URL:     $URL"
info "Headers: $HEADERS_JSON"
[[ $DRY_RUN -eq 1 ]] && info "DRY RUN (no write/restart)"

[[ -f "$CONFIG" ]] || { err "Config not found: $CONFIG"; exit 1; }

# Backup
STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP="${CONFIG}.bak-${STAMP}"
cp -a "$CONFIG" "$BACKUP"
ok "Backup created: $BACKUP"

# Create a temp file for atomic write
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT

# Update JSON (jq preferred)
if command -v jq >/dev/null 2>&1; then
  # Check existing & collision
  EXISTS=$(jq -r --arg name "$SERVICE" '(.mcpServers // {}) | has($name)' "$CONFIG")
  if [[ "$EXISTS" == "true" && $FORCE -ne 1 ]]; then
    err "Service '$SERVICE' already exists. Use --force to overwrite."
    exit 1
  fi

  jq --arg name "$SERVICE" --argjson obj "$SERVICE_OBJ" '
    . as $root
    | (if has("mcpServers") then . else . + {"mcpServers":{}} end)
    | .mcpServers[$name] = $obj
  ' "$CONFIG" > "$TMP"

else
  # Python fallback updater
  python3 - "$CONFIG" "$SERVICE" "$SERVICE_OBJ" > "$TMP" <<'PY'
import json,sys,io,os
cfg_path, name, obj_json = sys.argv[1], sys.argv[2], sys.argv[3]
with open(cfg_path, "r", encoding="utf-8") as f:
    data = json.load(f)
if not isinstance(data, dict): data = {}
m = data.get("mcpServers") or {}
if not isinstance(m, dict): m = {}
obj = json.loads(obj_json)
m[name] = obj
data["mcpServers"] = m
# Nice formatting
sys.stdout.write(json.dumps(data, indent=2, ensure_ascii=False))
PY
fi

# Validate final JSON
if command -v jq >/dev/null 2>&1; then
  jq -e . "$TMP" >/dev/null
else
  python3 - <<PY >/dev/null
import json,sys
json.load(open("$TMP","r",encoding="utf-8"))
PY
fi
ok "Config JSON validated."

# Write (unless dry run)
if [[ $DRY_RUN -eq 1 ]]; then
  info "Dry-run output left in: $TMP"
  exit 0
fi
mv "$TMP" "$CONFIG"
ok "Config updated."

# Restart central proxy (unless skipped)
if [[ $SKIP_RESTART -eq 1 ]]; then
  info "Skipping restart per --skip-restart"
else
  (cd "$PROXY_DIR" && docker compose restart mcp-proxy)
  ok "Central proxy restarted."

  # Health check root
  # curl -fsS "http://${CENTRAL_HOST}:${CENTRAL_PORT}/" >/dev/null
  # ok "Central proxy health check passed."
fi

# Optional SSE test through central proxy
if [[ $RUN_TEST -eq 1 ]]; then
  info "Running SSE smoke test via central route..."
  AUTH_HDR=()
  if [[ -n "$TEST_TOKEN" ]]; then
    AUTH_HDR=(-H "Authorization: Bearer ${TEST_TOKEN}")
  fi
  curl -N -m 5 -H 'Accept: text/event-stream' "${AUTH_HDR[@]}" \
    "http://${CENTRAL_HOST}:${CENTRAL_PORT}/${SERVICE}/sse" | head -n 5 || true
  ok "SSE test attempted (check output/logs above)."
fi