#!/bin/bash
# Master deployment script for MCP SSE services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load environment variables from secure location
ENV_FILE="/home/administrator/secrets/sse.env"
if [ -f "$ENV_FILE" ]; then
    set -a  # Automatically export variables
    source "$ENV_FILE"
    set +a
    echo -e "${GREEN}✓${NC} Loaded environment from $ENV_FILE"
else
    echo -e "${RED}✗${NC} Environment file not found: $ENV_FILE"
    exit 1
fi

# Ensure required networks exist
ensure_networks() {
    echo -e "${BLUE}Checking Docker networks...${NC}"
    
    if ! docker network ls | grep -q "litellm-net"; then
        echo -e "${YELLOW}Creating litellm-net network...${NC}"
        docker network create litellm-net
    fi
    
    if ! docker network ls | grep -q "postgres-net"; then
        echo -e "${YELLOW}postgres-net not found - it should already exist${NC}"
        echo -e "${YELLOW}Creating postgres-net network...${NC}"
        docker network create postgres-net
    fi
    
    echo -e "${GREEN}✓${NC} Networks ready"
}

# Health check function
check_service_health() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${BLUE}Checking health of $service_name on port $port...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "http://localhost:$port/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} $service_name is healthy"
            return 0
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            echo -e "${RED}✗${NC} $service_name health check failed after $max_attempts attempts"
            return 1
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
}

# Test all services
test_all_services() {
    echo -e "${BLUE}Testing all services...${NC}"
    
    local services=(
        "postgres:8001"
        "fetch:8002"
        "filesystem:8003"
        "github:8004" 
        "monitoring:8005"
    )
    
    for service_info in "${services[@]}"; do
        IFS=':' read -r service port <<< "$service_info"
        echo -e "${BLUE}Testing mcp-$service...${NC}"
        
        if check_service_health "mcp-$service" "$port"; then
            # Test SSE endpoint
            if curl -s --max-time 5 -H "Accept: text/event-stream" \
                "http://localhost:$port/sse" | head -1 | grep -q "event:"; then
                echo -e "${GREEN}✓${NC} mcp-$service SSE endpoint working"
            else
                echo -e "${YELLOW}⚠${NC} mcp-$service SSE endpoint may have issues"
            fi
        fi
    done
}

# Commands
case "$1" in
    up)
        echo -e "${GREEN}Starting all MCP SSE services...${NC}"
        ensure_networks
        docker compose up -d --build
        echo -e "${BLUE}Waiting for services to start...${NC}"
        sleep 10
        test_all_services
        echo -e "${GREEN}✓${NC} All services started successfully"
        echo ""
        echo "Service endpoints:"
        echo "  PostgreSQL:   http://localhost:8001/sse"
        echo "  Fetch:        http://localhost:8002/sse" 
        echo "  Filesystem:   http://localhost:8003/sse"
        echo "  GitHub:       http://localhost:8004/sse"
        echo "  Monitoring:   http://localhost:8005/sse"
        ;;
    
    down)
        echo -e "${YELLOW}Stopping all MCP SSE services...${NC}"
        docker compose down
        echo -e "${GREEN}✓${NC} All services stopped"
        ;;
    
    restart)
        echo -e "${YELLOW}Restarting all MCP SSE services...${NC}"
        $0 down
        sleep 5
        $0 up
        ;;
    
    status)
        echo -e "${BLUE}MCP SSE Services Status:${NC}"
        docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
        ;;
    
    logs)
        SERVICE=${2:-}
        if [ -z "$SERVICE" ]; then
            echo -e "${BLUE}Showing logs for all services...${NC}"
            docker compose logs --tail=50 -f
        else
            echo -e "${BLUE}Showing logs for mcp-$SERVICE...${NC}"
            if docker compose ps --services | grep -q "mcp-$SERVICE"; then
                docker compose logs --tail=50 -f "mcp-$SERVICE"
            else
                echo -e "${RED}✗${NC} Service mcp-$SERVICE not found"
                echo "Available services:"
                docker compose ps --services | grep "^mcp-"
            fi
        fi
        ;;
    
    test)
        SERVICE=${2:-}
        if [ -z "$SERVICE" ]; then
            test_all_services
        else
            case "$SERVICE" in
                postgres) check_service_health "mcp-postgres" 8001 ;;
                fetch) check_service_health "mcp-fetch" 8002 ;;
                filesystem) check_service_health "mcp-filesystem" 8003 ;;
                github) check_service_health "mcp-github" 8004 ;;
                monitoring) check_service_health "mcp-monitoring" 8005 ;;
                *)
                    echo -e "${RED}✗${NC} Unknown service: $SERVICE"
                    echo "Available services: postgres, fetch, filesystem, github, monitoring"
                    exit 1
                    ;;
            esac
        fi
        ;;
    
    build)
        echo -e "${BLUE}Building all Docker images...${NC}"
        docker compose build --no-cache
        echo -e "${GREEN}✓${NC} All images built"
        ;;
    
    clean)
        echo -e "${RED}Removing all MCP containers, volumes, and images...${NC}"
        read -p "Are you sure? This will remove all data. (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker compose down -v --rmi all
            docker system prune -f
            echo -e "${GREEN}✓${NC} Cleanup complete"
        else
            echo "Cleanup cancelled"
        fi
        ;;
    
    shell)
        SERVICE=${2:-postgres}
        echo -e "${BLUE}Opening shell in mcp-$SERVICE...${NC}"
        if docker ps --format "{{.Names}}" | grep -q "mcp-$SERVICE"; then
            docker exec -it "mcp-$SERVICE" /bin/bash
        else
            echo -e "${RED}✗${NC} Service mcp-$SERVICE is not running"
        fi
        ;;
    
    *)
        echo "MCP SSE Services - Deployment Manager"
        echo ""
        echo "Usage: $0 {command} [service]"
        echo ""
        echo "Commands:"
        echo "  up         Start all services"
        echo "  down       Stop all services" 
        echo "  restart    Restart all services"
        echo "  status     Show service status"
        echo "  logs       Show logs for all services or specific service"
        echo "  test       Test all services or specific service"
        echo "  build      Build all Docker images"
        echo "  clean      Remove all containers, volumes, and images"
        echo "  shell      Open shell in service container"
        echo ""
        echo "Services: postgres, fetch, filesystem, github, monitoring"
        echo ""
        echo "Examples:"
        echo "  $0 up                    # Start all services"
        echo "  $0 logs postgres         # Show postgres logs"
        echo "  $0 test fetch            # Test fetch service"
        echo "  $0 shell filesystem      # Open shell in filesystem service"
        exit 1
        ;;
esac