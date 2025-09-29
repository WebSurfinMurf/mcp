# TBXark Streamable HTTP Investigation Packet

## Context
Goal: expose `filesystem` MCP (stdio) via TBXark/mcp-proxy using the community-download Docker image + docker-compose, hitting `POST /filesystem/mcp` (Streamable HTTP) from Claude/Codex clients.

## Artifacts & Locations
- Proxy plan: `mcp/planhttp.md`
- Status tracker: `mcp/planhttp.status.md`
- Proxy config (active): `mcp/proxy/config.json`
- Proxy compose stack: `mcp/proxy/docker-compose.yml`
- Diagnostic script: `mcp/proxy/phase0-run.sh`
- Logs (latest run): `mcp/logs/filesystem-proxy-20250928-220927.log`

## Current Config Snapshots
```jsonc
// mcp/proxy/config.json
{
  "mcpProxy": {
    "addr": ":9090",
    "baseURL": "http://localhost:9090",
    "name": "Local MCP Proxy",
    "type": "streamable-http",
    "options": {
      "logEnabled": true,
      "panicIfInvalid": false
    }
  },
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem@0.2.3", "/workspace"],
      "env": {
        "NODE_NO_WARNINGS": "1"
      }
    }
  }
}
```

```yaml
# mcp/proxy/docker-compose.yml
version: "3.8"

services:
  mcp-proxy:
    image: ghcr.io/tbxark/mcp-proxy:latest
    container_name: mcp-proxy
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./config.json:/config.json
      - /home/administrator/projects:/workspace:ro
    networks:
      - mcp-net
    command: ["-config", "/config.json"]
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:9090/health"]
      interval: 30s
      timeout: 5s
      retries: 3

networks:
  mcp-net:
    external: true
```

## Diagnostic Script (Full)
```bash
# mcp/proxy/phase0-run.sh
#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${BASE_DIR}/.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="${LOG_DIR}/filesystem-proxy-${TIMESTAMP}.log"

failure=0

TMP_HEADERS_INIT="$(mktemp)"
TMP_BODY_INIT="$(mktemp)"
TMP_HEADERS_LIST="$(mktemp)"
TMP_BODY_LIST="$(mktemp)"
TMP_HEADERS_ROOT="$(mktemp)"
TMP_BODY_ROOT="$(mktemp)"
TMP_HEADERS_RAW="$(mktemp)"
TMP_BODY_RAW="$(mktemp)"
TMP_HEADERS_SSE="$(mktemp)"
TMP_BODY_SSE="$(mktemp)"
TMP_HEADERS_ROOT_SSE="$(mktemp)"
TMP_BODY_ROOT_SSE="$(mktemp)"
TMP_CONFIG_LS="$(mktemp)"

cleanup() {
  rm -f "${TMP_HEADERS_INIT}" "${TMP_BODY_INIT}" \
        "${TMP_HEADERS_LIST}" "${TMP_BODY_LIST}" \
        "${TMP_HEADERS_ROOT}" "${TMP_BODY_ROOT}" \
        "${TMP_HEADERS_RAW}" "${TMP_BODY_RAW}" \
        "${TMP_HEADERS_SSE}" "${TMP_BODY_SSE}" \
        "${TMP_HEADERS_ROOT_SSE}" "${TMP_BODY_ROOT_SSE}" \
        "${TMP_CONFIG_LS}"
}
trap cleanup EXIT

exec > >(tee -a "${LOG_FILE}") 2>&1

echo "=== Filesystem Proxy Deployment (TBXark community setup) ==="
echo "Run started: $(date)"
echo

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker command not found." >&2
  exit 1
fi

if ! command -v docker compose >/dev/null 2>&1; then
  echo "ERROR: docker compose plugin not found." >&2
  exit 1
fi

echo "--- Ensure docker network mcp-net exists ---"
if docker network inspect mcp-net >/dev/null 2>&1; then
  echo "mcp-net already present"
else
  docker network create mcp-net
  echo "Created docker network mcp-net"
fi

echo
cd "${BASE_DIR}"

echo "--- Pull latest TBXark/mcp-proxy image (community download) ---"
docker compose pull mcp-proxy

echo

echo "--- Launch/Update proxy via docker compose ---"
docker compose up -d

echo

echo "--- Container status ---"
docker ps --filter name=mcp-proxy

echo

echo "--- Proxy health (docker inspect) ---"
if ! docker inspect mcp-proxy --format '{{json .State.Health}}'; then
  echo "(health inspection failed)"
fi

echo

echo "--- Proxy binary help (/main --help) ---"
docker exec mcp-proxy /main --help || echo "(unable to run /main --help)"

echo

echo "--- Tail proxy logs (last 200 lines) ---"
docker logs --tail 200 mcp-proxy || echo "(proxy logs unavailable yet)"

echo

echo "--- Wait for service warmup (10s) ---"
sleep 10

echo

echo "--- Proxy config inside container ---"
docker exec mcp-proxy cat /config.json || echo "(unable to read /config.json)"

echo

echo "--- Proxy /config directory listing ---"
if docker exec mcp-proxy ls -R /config >"${TMP_CONFIG_LS}" 2>&1; then
  cat "${TMP_CONFIG_LS}"
else
  echo "(ls /config failed)"
  cat "${TMP_CONFIG_LS}"
fi

echo

echo "--- Streamable HTTP: initialize ---"
INIT_PAYLOAD='{"jsonrpc":"2.0","id":"1","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{}}}'
curl -sS -D "${TMP_HEADERS_INIT}" -o "${TMP_BODY_INIT}" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -X POST http://localhost:9090/filesystem/mcp \
  --data "${INIT_PAYLOAD}" || true

INIT_STATUS="$(awk 'NR==1 {print $2}' "${TMP_HEADERS_INIT}" 2>/dev/null || echo 0)"
if [[ "${INIT_STATUS}" != "200" && "${INIT_STATUS}" != "202" ]]; then
  echo "ERROR: initialize call returned HTTP ${INIT_STATUS}" >&2
  failure=1
  echo "--- Initialize response headers ---"
  cat "${TMP_HEADERS_INIT}"
  echo "--- Initialize response body ---"
  cat "${TMP_BODY_INIT}"
else
  echo "Initialize response headers:"
  cat "${TMP_HEADERS_INIT}"
  echo
  echo "Initialize response body:"
  cat "${TMP_BODY_INIT}"
fi

echo

SESSION_ID="$(awk 'tolower($1)=="mcp-session-id:" {print $2}' "${TMP_HEADERS_INIT}" | tr -d '\r')"
if [[ -z "${SESSION_ID}" ]]; then
  echo "WARNING: Mcp-Session-Id header not found; proceeding without session pinning"
else
  echo "Captured Mcp-Session-Id: ${SESSION_ID}"
fi

echo

echo "--- Streamable HTTP: tools/list ---"
if [[ "${INIT_STATUS}" == "200" || "${INIT_STATUS}" == "202" ]]; then
  LIST_PAYLOAD='{"jsonrpc":"2.0","id":"2","method":"tools/list","params":{}}'
  CURL_ARGS=(
    -sS -D "${TMP_HEADERS_LIST}" -o "${TMP_BODY_LIST}"
    -H 'Content-Type: application/json'
    -H 'Accept: application/json, text/event-stream'
    -X POST http://localhost:9090/filesystem/mcp
    --data "${LIST_PAYLOAD}"
  )
  if [[ -n "${SESSION_ID}" ]]; then
    CURL_ARGS=("-H" "Mcp-Session-Id: ${SESSION_ID}" "${CURL_ARGS[@]}")
  fi
  curl ${CURL_ARGS[@]} || true

  LIST_STATUS="$(awk 'NR==1 {print $2}' "${TMP_HEADERS_LIST}" 2>/dev/null || echo 0)"
  if [[ "${LIST_STATUS}" != "200" && "${LIST_STATUS}" != "202" ]]; then
    echo "ERROR: tools/list call returned HTTP ${LIST_STATUS}" >&2
    failure=1
    echo "--- tools/list response headers ---"
    cat "${TMP_HEADERS_LIST}"
    echo "--- tools/list response body ---"
    cat "${TMP_BODY_LIST}"
  else
    echo "tools/list response headers:"
    cat "${TMP_HEADERS_LIST}"
    echo
    echo "tools/list response body:"
    cat "${TMP_BODY_LIST}"
  fi
else
  echo "Skipping tools/list because initialize failed"
fi

echo

echo "--- HTTP Diag: GET / ---"
curl -sS -D "${TMP_HEADERS_ROOT}" -o "${TMP_BODY_ROOT}" http://localhost:9090/ || true
echo "Headers:"
cat "${TMP_HEADERS_ROOT}"
echo "Body:"
cat "${TMP_BODY_ROOT}"

echo

echo "--- HTTP Diag: POST /mcp (empty payload) ---"
curl -sS -D "${TMP_HEADERS_RAW}" -o "${TMP_BODY_RAW}" -X POST http://localhost:9090/mcp -H 'Content-Type: application/json' --data '{}' || true
echo "Headers:"
cat "${TMP_HEADERS_RAW}"
echo "Body:"
cat "${TMP_BODY_RAW}"

echo

echo "--- HTTP Diag: GET /filesystem/sse (5s timeout) ---"
curl -sS -D "${TMP_HEADERS_SSE}" -o "${TMP_BODY_SSE}" --max-time 5 -H 'Accept: text/event-stream' http://localhost:9090/filesystem/sse || true
echo "Headers:"
cat "${TMP_HEADERS_SSE}"
if [[ -s "${TMP_BODY_SSE}" ]]; then
  echo "Body:"
  cat "${TMP_BODY_SSE}"
else
  echo "Body: (empty or truncated due to timeout)"
fi

echo

echo "--- HTTP Diag: GET /sse (5s timeout) ---"
curl -sS -D "${TMP_HEADERS_ROOT_SSE}" -o "${TMP_BODY_ROOT_SSE}" --max-time 5 -H 'Accept: text/event-stream' http://localhost:9090/sse || true
echo "Headers:"
cat "${TMP_HEADERS_ROOT_SSE}"
if [[ -s "${TMP_BODY_ROOT_SSE}" ]]; then
  echo "Body:"
  cat "${TMP_BODY_ROOT_SSE}"
else
  echo "Body: (empty or truncated due to timeout)"
fi

echo

echo "--- Final proxy logs snapshot (last 200 lines) ---"
docker logs --tail 200 mcp-proxy || echo "(proxy logs unavailable)"

echo

echo "--- docker inspect (State) ---"
docker inspect mcp-proxy --format '{{json .State}}' || echo "(state inspection failed)"

echo

echo "Logs collected at ${LOG_FILE}"
if [[ "${failure}" -ne 0 ]]; then
  echo "COMPLETED WITH ERRORS"
else
  echo "COMPLETED SUCCESSFULLY"
fi

echo "Run finished: $(date)"
```

## Test Results (Latest Run)
- Script command: `mcp/proxy/phase0-run.sh`
- Log file: `mcp/logs/filesystem-proxy-20250928-220927.log`
- Key observations:
  - Proxy logs: `Starting streamable-http server` / `streamable-http server listening on :9090`
  - `/filesystem/mcp`, `/mcp`, `/filesystem/sse`, `/sse`, `/` all respond with `HTTP/1.1 404 Not Found`
  - Initialize request does not return `Mcp-Session-Id`
  - `docker exec mcp-proxy /main --help` shows streamable-http support
  - `/config.json` inside container matches host config; `/config` directory absent because config is mounted at root
  - Health check now passes (curl-based)

## Supporting Notes
- Previous health check using `wget` failed because `wget` is absent in the proxy image; switched to `curl`.
- SSE endpoints also return 404, so no MCP routes appear active despite log claims.
- `mcp/http404.md` and `question_for_research_{6,7}.txt` contain community Q&A attempts; no solution provided yet.

## To Be Proven (Maybe True)
- The published `ghcr.io/tbxark/mcp-proxy:latest` image may not actually wire stdio services into streamable HTTP routes despite logging that it does; possibly a regression or missing flag/version mismatch.
- The proxy might require a different config layout (e.g., mounting to `/config/config.json` or adding `type: stdio`) or an older/newer tag (`v0.39.1`?) to activate HTTP handlers.
- Because `/filesystem/sse` also 404s, there could be a broader routing bug: service registration logs succeed, but the HTTP router never attaches handlers when `mcpServers.<name>` is a stdio command without explicit `type`.
- If TBXark expects `/config/config.json`, placing the file at root might cause handlers to be missing even though `/config.json` is read correctly (needs confirmation).
- The proxy may only expose a single aggregate `/mcp` endpoint regardless of service name; our tests might need to hit `/mcp` with additional headers or JSON structure (though direct `/mcp` currently 404s). Further spec review required.

---
*Prepared for cross-agent debugging to avoid duplicate effort and inform future troubleshooting.*
