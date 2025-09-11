#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== MCP TimescaleDB Server Deployment ===${NC}"
echo ""

# Build the Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t mcp-timescaledb:latest .
echo -e "${GREEN}✓ Docker image built${NC}"

# Stop and remove existing container if it exists
echo -e "${YELLOW}Cleaning up existing container...${NC}"
docker stop mcp-timescaledb 2>/dev/null || true
docker rm mcp-timescaledb 2>/dev/null || true
echo -e "${GREEN}✓ Cleanup complete${NC}"

# Create networks if they don't exist
echo -e "${YELLOW}Setting up networks...${NC}"
docker network create observability-net 2>/dev/null || true
docker network create postgres-net 2>/dev/null || true
echo -e "${GREEN}✓ Networks ready${NC}"

# Run the MCP server
echo -e "${YELLOW}Starting MCP TimescaleDB server...${NC}"
docker run -d \
  --name mcp-timescaledb \
  --restart unless-stopped \
  --network observability-net \
  --env-file /home/administrator/projects/mcp-timescaledb/.env \
  --log-driver json-file \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  mcp-timescaledb:latest

echo -e "${GREEN}✓ MCP TimescaleDB server started${NC}"

# Connect to additional networks
echo -e "${YELLOW}Connecting to additional networks...${NC}"
docker network connect postgres-net mcp-timescaledb 2>/dev/null || true
echo -e "${GREEN}✓ Connected to postgres-net${NC}"

# Check container status
echo -e "${BLUE}=== Container Status ===${NC}"
docker ps | grep mcp-timescaledb

# Show logs
echo ""
echo -e "${BLUE}=== Recent Logs ===${NC}"
sleep 2
docker logs mcp-timescaledb --tail 10

echo ""
echo -e "${GREEN}✅ MCP TimescaleDB server deployment complete!${NC}"
echo ""
echo -e "${YELLOW}Available tools:${NC}"
echo "  - tsdb_query: Execute SELECT queries"
echo "  - tsdb_execute: Execute INSERT/UPDATE/DELETE/CREATE"
echo "  - tsdb_create_hypertable: Convert table to hypertable"
echo "  - tsdb_show_hypertables: List all hypertables"
echo "  - tsdb_show_chunks: Show chunks for a hypertable"
echo "  - tsdb_compression_stats: Show compression statistics"
echo "  - tsdb_add_compression: Add compression policy"
echo "  - tsdb_continuous_aggregate: Create continuous aggregate"
echo "  - tsdb_time_bucket_query: Execute time-bucket aggregations"
echo "  - tsdb_database_stats: Get database statistics"