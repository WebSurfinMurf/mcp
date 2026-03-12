#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_FILE="$HOME/projects/secrets/mcp-vikunja.env"

if [[ ! -f "$SECRETS_FILE" ]]; then
    echo "ERROR: secrets file not found: $SECRETS_FILE"
    echo "Create it with:"
    echo "  VIKUNJA_API_URL=http://vikunja:3456"
    echo "  VIKUNJA_SERVICE_USERNAME=<service-account-username>"
    echo "  VIKUNJA_SERVICE_PASSWORD=<service-account-password>"
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "$SECRETS_FILE"
# Source main vikunja.env for VIKUNJA_JWT_SECRET if not in mcp-vikunja.env
VIKUNJA_SECRETS="$HOME/projects/secrets/vikunja.env"
if [[ -f "$VIKUNJA_SECRETS" ]]; then
    source "$VIKUNJA_SECRETS"
fi
set +a

cd "$SCRIPT_DIR"

echo "Building mcp-vikunja image..."
docker compose build

echo "Starting mcp-vikunja..."
docker compose up -d

echo "Waiting for health check..."
sleep 5

docker compose ps
echo "mcp-vikunja deployed. Endpoint: http://mcp-vikunja:8000/mcp"
