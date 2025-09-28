#!/bin/bash
set -e

echo "Deploying all MCP service containers..."

SERVICES_DIR="/home/administrator/projects/mcp"

SERVICES=(
    "filesystem"
    "timescaledb"
    "minio"
    "n8n"
    "playwright"
)

for service in "${SERVICES[@]}"; do
    if [ -f "${SERVICES_DIR}/${service}/deploy.sh" ]; then
        echo "--- Deploying ${service} ---"
        (cd "${SERVICES_DIR}/${service}" && ./deploy.sh)
    else
        echo "WARNING: No deploy.sh script found for ${service}. Skipping."
    fi
done

echo ""
echo "Deployment commands issued. Verifying status..."
docker ps | grep "mcp-"

echo "All available MCP services have been started."
