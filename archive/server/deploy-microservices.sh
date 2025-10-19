#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== MCP Microservice Architecture Deployment ===${NC}"
echo -e "${YELLOW}Deploying centralized MCP server with dedicated service containers${NC}"

PROJECT_NAME="mcp-server"
PROJECT_DIR="/home/administrator/projects/mcp/server"
SECRETS_FILE="$HOME/projects/secrets/mcp-server.env"

# Change to project directory
cd "$PROJECT_DIR"

# Validate prerequisites
echo -e "${YELLOW}Validating prerequisites...${NC}"
if [ ! -f "$SECRETS_FILE" ]; then
    echo -e "${RED}Error: Secrets file not found at $SECRETS_FILE${NC}"
    exit 1
fi

# Load secrets for validation
source "$SECRETS_FILE"

# Check required external services
echo -e "${YELLOW}Checking external service availability...${NC}"
if ! docker ps | grep -q "postgres"; then
    echo -e "${RED}Error: PostgreSQL container not running${NC}"
    exit 1
fi

if ! docker ps | grep -q "timescaledb"; then
    echo -e "${RED}Error: TimescaleDB container not running${NC}"
    exit 1
fi

if ! docker ps | grep -q "n8n"; then
    echo -e "${RED}Error: n8n container not running${NC}"
    exit 1
fi

echo -e "${GREEN}✓ External services validated${NC}"

# Create MCP internal network if it doesn't exist
echo -e "${YELLOW}Setting up MCP internal network...${NC}"
if ! docker network ls | grep -q "mcp-internal"; then
    docker network create mcp-internal --driver bridge --subnet 172.30.0.0/24
    echo -e "${GREEN}✓ MCP internal network created${NC}"
else
    echo -e "${GREEN}✓ MCP internal network already exists${NC}"
fi

# Stop existing containers if running
echo -e "${YELLOW}Stopping existing MCP containers...${NC}"
docker compose -f docker-compose.microservices.yml down 2>/dev/null || true

# Build custom images
echo -e "${YELLOW}Building Playwright MCP container...${NC}"
cd /home/administrator/projects/mcp/evaluation/playwright-official
docker build -t mcp-playwright:latest .

echo -e "${YELLOW}Building TimescaleDB MCP container...${NC}"
cd /home/administrator/projects/mcp/timescaledb
docker build -t mcp-timescaledb:latest .

# Return to project directory
cd "$PROJECT_DIR"

# Deploy microservice stack
echo -e "${YELLOW}Deploying MCP microservice stack...${NC}"
docker compose -f docker-compose.microservices.yml up -d

# Wait for services to start
echo -e "${YELLOW}Waiting for services to initialize...${NC}"
sleep 30

# Health checks
echo -e "${YELLOW}Running health checks...${NC}"

# Check main MCP server
if curl -f -s http://mcp.linuxserver.lan:8001/health > /dev/null; then
    echo -e "${GREEN}✓ Main MCP server healthy${NC}"
else
    echo -e "${RED}✗ Main MCP server health check failed${NC}"
fi

# Check container status
echo -e "${YELLOW}Container status:${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep mcp

# Show logs for troubleshooting
echo -e "${YELLOW}Recent container logs:${NC}"
for container in mcp-server mcp-n8n mcp-playwright mcp-timescaledb; do
    if docker ps | grep -q "$container"; then
        echo -e "${BLUE}=== $container logs ===${NC}"
        docker logs "$container" --tail 5 2>/dev/null || echo "No logs available"
        echo ""
    fi
done

echo -e "${GREEN}=== MCP Microservice Deployment Complete ===${NC}"
echo -e "🔗 Internal Access: http://mcp.linuxserver.lan"
echo -e "🔒 External Access: https://mcp.ai-servicers.com"
echo -e "📊 API Documentation: http://mcp.linuxserver.lan:8001/docs"
echo -e "🔍 Health Check: http://mcp.linuxserver.lan:8001/health"
echo -e "📋 Tools List: http://mcp.linuxserver.lan:8001/tools"
echo ""
echo -e "${BLUE}Microservice Endpoints:${NC}"
echo -e "• n8n MCP: http://mcp-n8n:3000 (internal)"
echo -e "• Playwright MCP: mcp-playwright:stdio (internal)"
echo -e "• TimescaleDB MCP: mcp-timescaledb:stdio (internal)"
echo ""
echo -e "View logs: ${YELLOW}docker compose -f docker-compose.microservices.yml logs -f${NC}"