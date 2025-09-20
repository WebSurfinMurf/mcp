#!/usr/bin/env bash
set -euo pipefail

: "${LITELLM_HOST:=linuxserver.lan}"
: "${LITELLM_PORT:=4100}"
: "${LITELLM_API_KEY:=sk-e0b742bc6575adf26c7d356c49c78d8fd08119fcde1d6e188d753999b5f956fc}"
: "${MCP_SERVERS:=mcp_postgres,mcp_filesystem}"
: "${LITELLM_IP:=}"

curl_args=(
  -sS -N -X POST
  -H "Authorization: Bearer ${LITELLM_API_KEY}"
  -H "x-mcp-servers: ${MCP_SERVERS}"
  -H "Accept: application/json, text/event-stream"
  -H "Content-Type: application/json"
)

if [[ -n "${LITELLM_IP}" ]]; then
  curl_args+=("--resolve" "${LITELLM_HOST}:${LITELLM_PORT}:${LITELLM_IP}")
fi

curl "${curl_args[@]}" \
  -d '{"jsonrpc":"2.0","id":"tools-list","method":"tools/list","params":{}}' \
  "http://${LITELLM_HOST}:${LITELLM_PORT}/mcp/tools"
