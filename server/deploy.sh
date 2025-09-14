#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== MCP Server Deployment ===${NC}"

PROJECT_NAME="mcp-server"
PROJECT_DIR="/home/administrator/projects/mcp/server"
DATA_DIR="/home/administrator/projects/data/$PROJECT_NAME"
SECRETS_FILE="/home/administrator/secrets/$PROJECT_NAME.env"

# Validate prerequisites
echo -e "${YELLOW}Validating prerequisites...${NC}"

if [ ! -f "$SECRETS_FILE" ]; then
    echo -e "${RED}Error: Secrets file not found at $SECRETS_FILE${NC}"
    echo "Please ensure the secrets file exists and is properly configured."
    exit 1
fi

# Check required environment files
for env_file in postgres.env minio.env; do
    if [ ! -f "/home/administrator/secrets/$env_file" ]; then
        echo -e "${YELLOW}Warning: $env_file not found in secrets directory${NC}"
    fi
done

# Validate Docker networks
echo -e "${YELLOW}Checking Docker networks...${NC}"
required_networks="litellm-net postgres-net traefik-proxy keycloak-net observability-net"
missing_networks=""

for network in $required_networks; do
    if ! docker network ls --format "{{.Name}}" | grep -q "^${network}$"; then
        missing_networks="$missing_networks $network"
    fi
done

if [ ! -z "$missing_networks" ]; then
    echo -e "${RED}Error: Missing Docker networks:$missing_networks${NC}"
    echo "Please ensure all required networks exist before deployment."
    exit 1
fi

# Create data directory
mkdir -p "$DATA_DIR"
echo -e "${GREEN}✓ Data directory created: $DATA_DIR${NC}"

# Navigate to project directory
cd "$PROJECT_DIR"

# Load environment variables for validation
echo -e "${YELLOW}Loading configuration...${NC}"
set -a  # Export all variables
source "$SECRETS_FILE"
set +a

# Validate critical environment variables
required_vars="POSTGRES_USER POSTGRES_PASSWORD MINIO_ROOT_USER MINIO_ROOT_PASSWORD OAUTH2_PROXY_CLIENT_SECRET OAUTH2_PROXY_COOKIE_SECRET"
missing_vars=""

for var in $required_vars; do
    if [ -z "${!var}" ]; then
        missing_vars="$missing_vars $var"
    fi
done

if [ ! -z "$missing_vars" ]; then
    echo -e "${RED}Error: Missing required environment variables:$missing_vars${NC}"
    echo "Please configure these variables in $SECRETS_FILE"
    exit 1
fi

# Check for placeholder values
if [ "$OAUTH2_PROXY_CLIENT_SECRET" = "CHANGE_ME_IN_PHASE_4" ] || [ "$OAUTH2_PROXY_COOKIE_SECRET" = "CHANGE_ME_IN_PHASE_4" ]; then
    echo -e "${YELLOW}Warning: OAuth2 proxy contains placeholder values${NC}"
    echo "Authentication may not work until Keycloak client is properly configured"
fi

# Stop existing containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker compose down 2>/dev/null || true

# Deploy new containers
echo -e "${YELLOW}Deploying containers...${NC}"
docker compose up -d

# Wait for services to start
echo -e "${YELLOW}Waiting for services to start...${NC}"
sleep 15

# Health checks
echo -e "${YELLOW}Checking service health...${NC}"

# Check container status
if docker ps | grep -q "$PROJECT_NAME"; then
    echo -e "${GREEN}✓ Containers are running${NC}"
else
    echo -e "${RED}✗ Container deployment failed${NC}"
    echo "Container logs:"
    docker-compose logs --tail 20
    exit 1
fi

# Test main application health endpoint
echo -e "${YELLOW}Testing application health...${NC}"
if timeout 30 bash -c 'until curl -sf http://localhost:8000/health > /dev/null; do sleep 2; done'; then
    echo -e "${GREEN}✓ Application health check passed${NC}"

    # Get health check details
    health_info=$(curl -s http://localhost:8000/health | jq -r '.tools_count // "unknown"')
    echo -e "${GREEN}  Tools loaded: $health_info${NC}"
else
    echo -e "${YELLOW}⚠ Application health check failed (may need more time to start)${NC}"
    echo "Checking application logs:"
    docker logs mcp-server --tail 10
fi

# Test OAuth2 proxy
echo -e "${YELLOW}Testing OAuth2 proxy...${NC}"
if curl -sf -I http://localhost:4180/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ OAuth2 proxy is responding${NC}"
else
    echo -e "${YELLOW}⚠ OAuth2 proxy health check failed${NC}"
    echo "OAuth2 proxy logs:"
    docker logs mcp-server-auth-proxy --tail 5
fi

# Test tools endpoint
echo -e "${YELLOW}Testing tools API...${NC}"
if tools_response=$(curl -s http://localhost:8000/tools 2>/dev/null); then
    tools_count=$(echo "$tools_response" | jq -r '.count // "unknown"')
    echo -e "${GREEN}✓ Tools API responding: $tools_count tools available${NC}"

    # Show tool categories
    categories=$(echo "$tools_response" | jq -r '.categories | keys[]' 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
    if [ ! -z "$categories" ]; then
        echo -e "${GREEN}  Categories: $categories${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Tools API not responding yet${NC}"
fi

echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo -e "Service Status:"
echo -e "  Main Application: http://localhost:8000"
echo -e "  External URL: https://mcp.ai-servicers.com"
echo -e "  Health Check: https://mcp.ai-servicers.com/health"
echo -e "  API Docs: https://mcp.ai-servicers.com/docs"
echo -e "  Tools List: https://mcp.ai-servicers.com/tools"
echo ""
echo -e "Management Commands:"
echo -e "  View logs: ${YELLOW}docker compose logs -f${NC}"
echo -e "  Restart: ${YELLOW}docker compose restart${NC}"
echo -e "  Stop: ${YELLOW}docker compose down${NC}"
echo ""

# Final service validation
echo -e "${YELLOW}Final validation...${NC}"
if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(mcp-server|mcp-server-auth-proxy)"; then
    echo -e "${GREEN}✓ All services deployed successfully${NC}"
else
    echo -e "${YELLOW}⚠ Some services may have issues${NC}"
    exit 1
fi