#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
PROJECT_ROOT="$(cd "${BASE_DIR}/.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="${LOG_DIR}/filesystem-proxy-${TIMESTAMP}.log"

failure=0

# Temporary files for curl diagnostics
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
  rm -f \
    "${TMP_HEADERS_INIT}" "${TMP_BODY_INIT}" \
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
  echo "ERROR: docker command not found. Please install Docker before running this script." >&2
  exit 1
fi

if ! command -v docker compose >/dev/null 2>&1; then
  echo "ERROR: docker compose plugin not found. Install Docker Compose v2 (docker CLI plugin)." >&2
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
if ! docker exec mcp-proxy /main --help; then
  echo "(unable to run /main --help)"
fi

echo

echo "--- Tail proxy logs (last 200 lines) ---"
docker logs --tail 200 mcp-proxy || echo "(proxy logs unavailable yet)"

echo

echo "--- Wait for service warmup (10s) ---"
sleep 10

echo

echo "--- Proxy config inside container ---"
if ! docker exec mcp-proxy cat /config/config.json; then
  echo "(unable to read /config/config.json)"
fi

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
  # shellcheck disable=SC2068
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
