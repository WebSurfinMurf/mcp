#!/usr/bin/env bash
set -euo pipefail

# add-bridge.sh
# Scaffold a sidecar "bridge" container that runs a stdio MCP tool inside
# TBXark/mcp-proxy, exposing a stable SSE endpoint for the central proxy.
#
# Creates:
#   projects/mcp/<service>/bridge/
#     ├─ Dockerfile
#     ├─ docker-compose.yml
#     └─ config/config.json
#
# Requirements:
#   - External Docker network "mcp-net" already created
#   - You provide the stdio MCP tool package + version and a port
#
# Usage examples (copy/paste):
#
#   # Filesystem (Node) — needs workspace mount
#   ./add-bridge.sh \
#     --service filesystem \
#     --runtime node \
#     --pkg @modelcontextprotocol/server-filesystem \
#     --version 0.2.3 \
#     --bin-cmd mcp-server-filesystem \
#     --port 9071 \
#     --workspace /home/administrator/projects
#
#   # Fetch (Python)
#   ./add-bridge.sh \
#     --service fetch \
#     --runtime python \
#     --pkg mcp-server-fetch \
#     --version 0.1.4 \
#     --module mcp_server_fetch \
#     --port 9072
#
# Optional flags:
#   --publish              Publish host port (e.g., 9071:9071). NOT recommended in prod.
#   --with-auth            Require token at the bridge (uses ${MCP_PROXY_TOKEN}).
#   --mcp-net <name>       Docker network name (default: mcp-net)
#   --image-tag <tag>      Override image tag (default computed)
#
# After scaffold, build & start:
#   cd projects/mcp/<service>/bridge && docker compose up -d --build
#
# Then add to central proxy (config/config.json):
#   "<service>": { "url": "http://mcp-<service>-bridge:<port>/<service>/sse" }

# Defaults
MCP_NET="mcp-net"
PUBLISH=0
WITH_AUTH=0
SERVICE=""
RUNTIME=""
PKG=""
VERSION=""
BIN_CMD=""
MODULE=""
PORT=""
WORKSPACE=""
IMAGE_TAG=""

red()   { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
cyan()  { printf "\033[36m%s\033[0m\n" "$*"; }

usage() {
  cat <<EOF
Usage:
  $0 --service <name> --runtime <node|python> --pkg <package> --version <ver> --port <port> [options]

Required:
  --service <name>        Logical service name (e.g., filesystem, fetch)
  --runtime <node|python> Runtime for the stdio tool
  --pkg <package>         Package to install (npm or pip)
  --version <ver>         Package version to pin
  --port <port>           Bridge listen port (e.g., 9071)

Node-specific:
  --bin-cmd <cmd>         Executable to run (e.g., mcp-server-filesystem)
  --workspace <path>      Optional host path to mount at /workspace (ro)

Python-specific:
  --module <module>       If set, run with: python3 -m <module>
                          Else we'll try to run console script named like the package

Optional:
  --publish               Also publish host port "<port>:<port>" (debug only)
  --with-auth             Require "\${MCP_PROXY_TOKEN}" at the bridge
  --mcp-net <name>        Docker network (default: mcp-net)
  --image-tag <tag>       Override built image tag

Examples:
  See header of this file.
EOF
  exit 1
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --service)   SERVICE="$2"; shift 2 ;;
    --runtime)   RUNTIME="$2"; shift 2 ;;
    --pkg)       PKG="$2"; shift 2 ;;
    --version)   VERSION="$2"; shift 2 ;;
    --bin-cmd)   BIN_CMD="$2"; shift 2 ;;
    --module)    MODULE="$2"; shift 2 ;;
    --port)      PORT="$2"; shift 2 ;;
    --workspace) WORKSPACE="$2"; shift 2 ;;
    --publish)   PUBLISH=1; shift ;;
    --with-auth) WITH_AUTH=1; shift ;;
    --mcp-net)   MCP_NET="$2"; shift 2 ;;
    --image-tag) IMAGE_TAG="$2"; shift 2 ;;
    -h|--help)   usage ;;
    *) red "Unknown option: $1"; usage ;;
  esac
done

# Validate
[[ -z "$SERVICE"  ]] && red "--service is required" && usage
[[ -z "$RUNTIME"  ]] && red "--runtime is required" && usage
[[ -z "$PKG"      ]] && red "--pkg is required" && usage
[[ -z "$VERSION"  ]] && red "--version is required" && usage
[[ -z "$PORT"     ]] && red "--port is required" && usage
if [[ "$RUNTIME" != "node" && "$RUNTIME" != "python" ]]; then
  red "--runtime must be 'node' or 'python'"; usage
fi
if [[ "$RUNTIME" == "node" && -z "$BIN_CMD" ]]; then
  # Try common default for filesystem
  if [[ "$PKG" == "@modelcontextprotocol/server-filesystem" ]]; then
    BIN_CMD="mcp-server-filesystem"
  else
    red "--bin-cmd is required for node runtime (can't infer binary name for $PKG)"
    exit 1
  fi
fi

# Paths
BASE_DIR="/home/administrator/projects/mcp/${SERVICE}/bridge"
CFG_DIR="${BASE_DIR}/config"
mkdir -p "${CFG_DIR}"

# Image tag
if [[ -z "$IMAGE_TAG" ]]; then
  IMAGE_TAG="local/mcp-${SERVICE}-bridge:${VERSION}-${RUNTIME}"
fi

cyan "Scaffolding ${SERVICE} bridge at: ${BASE_DIR}"

############################################################
# Dockerfile
############################################################
DOCKERFILE="${BASE_DIR}/Dockerfile"
if [[ "$RUNTIME" == "node" ]]; then
  cat > "$DOCKERFILE" <<EOF
FROM ghcr.io/tbxark/mcp-proxy:v0.39.1

# Add Node/npm (alpine)
RUN apk add --no-cache nodejs npm

# Preinstall tool to avoid runtime network fetch
RUN npm i -g ${PKG}@${VERSION}

WORKDIR /app
COPY config /config

EXPOSE ${PORT}
CMD ["/app/mcp-proxy", "-config", "/config/config.json"]
EOF
else
  cat > "$DOCKERFILE" <<EOF
FROM ghcr.io/tbxark/mcp-proxy:v0.39.1

# Add Python + pip (alpine)
RUN apk add --no-cache python3 py3-pip

# Preinstall tool to avoid runtime network fetch
RUN pip install --no-cache-dir ${PKG}==${VERSION}

WORKDIR /app
COPY config /config

EXPOSE ${PORT}
CMD ["/app/mcp-proxy", "-config", "/config/config.json"]
EOF
fi

############################################################
# config.json
############################################################
CONFIG_JSON="${CFG_DIR}/config.json"

AUTH_BLOCK=""
if [[ $WITH_AUTH -eq 1 ]]; then
  AUTH_BLOCK=', "authTokens": ["${MCP_PROXY_TOKEN}"]'
fi

if [[ "$RUNTIME" == "node" ]]; then
  # Build args array (include /workspace if provided)
  ARGS_JSON="[]"
  if [[ -n "$WORKSPACE" ]]; then
    ARGS_JSON='["/workspace"]'
  fi

  cat > "$CONFIG_JSON" <<EOF
{
  "mcpProxy": {
    "addr": ":${PORT}",
    "name": "${SERVICE}-bridge",
    "options": { "logEnabled": true, "panicIfInvalid": false${AUTH_BLOCK} }
  },
  "mcpServers": {
    "${SERVICE}": {
      "command": "${BIN_CMD}",
      "args": ${ARGS_JSON}
    }
  }
}
EOF

else
  # Python command: prefer module if provided; else try console script = package name
  PY_CMD=""
  PY_ARGS="[]"
  if [[ -n "$MODULE" ]]; then
    PY_CMD="python3"
    PY_ARGS="[\"-m\", \"${MODULE}\"]"
  else
    # Best-effort console script equals package name
    PY_CMD="${PKG}"
    PY_ARGS="[]"
  fi

  cat > "$CONFIG_JSON" <<EOF
{
  "mcpProxy": {
    "addr": ":${PORT}",
    "name": "${SERVICE}-bridge",
    "options": { "logEnabled": true, "panicIfInvalid": false${AUTH_BLOCK} }
  },
  "mcpServers": {
    "${SERVICE}": {
      "command": "${PY_CMD}",
      "args": ${PY_ARGS}
    }
  }
}
EOF
fi

############################################################
# docker-compose.yml
############################################################
COMPOSE_YML="${BASE_DIR}/docker-compose.yml"
PORTS_LINE=""
if [[ $PUBLISH -eq 1 ]]; then
  PORTS_LINE="      - \"${PORT}:${PORT}\""
fi

WORKSPACE_VOL=""
if [[ -n "$WORKSPACE" ]]; then
  WORKSPACE_VOL="      - ${WORKSPACE}:/workspace:ro"
fi

cat > "$COMPOSE_YML" <<EOF
version: "3.8"
services:
  mcp-${SERVICE}-bridge:
    build: .
    image: ${IMAGE_TAG}
    container_name: mcp-${SERVICE}-bridge
    restart: unless-stopped
    networks: ["${MCP_NET}"]
$( [[ -n "$PORTS_LINE" ]] && echo "    ports:" && echo "${PORTS_LINE}" )
    volumes:
${WORKSPACE_VOL:-"      # no volumes"}
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:${PORT}/"]
      interval: 30s
      timeout: 5s
      retries: 3
    stop_grace_period: 10s
    deploy:
      resources:
        limits:
          memory: 256M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  ${MCP_NET}:
    external: true
EOF

green "✓ Scaffold complete."

cat <<NEXT

Build & run this bridge:

  cd ${BASE_DIR}
  docker compose up -d --build

Central proxy config entry (add to /home/administrator/projects/mcp/proxy/config/config.json):

  "${SERVICE}": { "url": "http://mcp-${SERVICE}-bridge:${PORT}/${SERVICE}/sse" }

Then reload central proxy:

  cd /home/administrator/projects/mcp/proxy
  docker compose restart mcp-proxy

Smoke test via central proxy:

  export MCP_PROXY_TOKEN=\${MCP_PROXY_TOKEN:-changeme-token}
  curl -N -H 'Accept: text/event-stream' -H "Authorization: Bearer \${MCP_PROXY_TOKEN}" \\
    http://linuxserver.lan:9090/${SERVICE}/sse

Notes:
- For production, DO NOT publish the bridge port (--publish). Keep it cluster-internal.
- If you must publish, use --with-auth and set MCP_PROXY_TOKEN in the bridge environment.
- For filesystem-like tools, pass --workspace /host/path to mount at /workspace:ro.
NEXT