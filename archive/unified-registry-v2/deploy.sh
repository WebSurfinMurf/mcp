#!/bin/bash
# Universal MCP Deployment Pipeline
# Handles both stdio (for Claude) and SSE (for web) modes

set -e  # Exit on error

# Configuration
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_NAME="mcp-unified-registry-v2"
VENV_PATH="$PROJECT_DIR/venv"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
CONFIG_FILE="$PROJECT_DIR/config.ini"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}==> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

usage() {
    cat << EOF
${BLUE}MCP Deployment Pipeline${NC}
-----------------------
Usage: $0 {setup|run|test|clean|status|register|register-all}

Commands:
  setup                    Create virtual environment and install dependencies
  run <service> <mode>     Run an MCP service (mode: stdio|sse)
  test [service]          Run test suite (optionally for specific service)
  clean                   Remove virtual environment and cache
  status                  Show status of all services
  register <service>      Register service with Claude Code configuration
  register-all            Register all available services with Claude Code

Examples:
  $0 setup                # Initial setup
  $0 run postgres stdio   # Run PostgreSQL service in stdio mode
  $0 run postgres sse     # Run PostgreSQL service in SSE mode
  $0 test postgres        # Test PostgreSQL service
  $0 status              # Check all services
  $0 register postgres    # Add postgres to Claude Code config

Available services:
  postgres    - PostgreSQL database operations
  filesystem  - File system operations
  github      - GitHub API operations
  monitoring  - System monitoring and logs
  n8n        - Workflow automation
  playwright  - Browser automation
  timescaledb - Time-series database

EOF
    exit 1
}

do_setup() {
    print_header "Setting up MCP environment..."
    
    # Check Python version
    if ! python3 --version | grep -q "3\.[89]\|3\.1[0-9]"; then
        print_warning "Python 3.8+ recommended. Current version:"
        python3 --version
    fi
    
    # Create virtual environment
    if [ ! -d "$VENV_PATH" ]; then
        print_header "Creating Python virtual environment..."
        python3 -m venv "$VENV_PATH"
        print_success "Virtual environment created"
    else
        print_warning "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    
    # Upgrade pip
    print_header "Upgrading pip..."
    pip install --upgrade pip --quiet
    
    # Create requirements.txt if not exists
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        print_header "Creating requirements.txt..."
        cat > "$REQUIREMENTS_FILE" << 'EOF'
# Core dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic[email]==2.5.0

# Database
psycopg2-binary==2.9.9
redis==5.0.1
sqlalchemy==2.0.23

# Utilities
python-dotenv==1.0.0
pyyaml==6.0.1
requests==2.31.0
aiofiles==23.2.1
httpx==0.25.2

# Development
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
mypy==1.7.0
ruff==0.1.6

# Logging
python-json-logger==2.0.7
structlog==23.2.0
EOF
        print_success "Requirements file created"
    fi
    
    # Install dependencies
    print_header "Installing dependencies from requirements.txt..."
    pip install -r "$REQUIREMENTS_FILE" --quiet
    print_success "Dependencies installed"
    
    # Generate default config if not exists
    if [ ! -f "$CONFIG_FILE" ]; then
        print_header "Generating default configuration..."
        python3 << 'PYTHON_EOF'
import configparser
config = configparser.ConfigParser()
config['general'] = {
    'log_level': 'INFO',
    'state_backend': 'memory'
}
config['security'] = {
    'read_only': 'false',
    'max_request_size_mb': '10'
}
config['sse'] = {
    'host': '0.0.0.0',
    'port': '8000'
}
config['stdio'] = {
    'buffer_size': '4096'
}
with open('config.ini', 'w') as f:
    config.write(f)
print('✓ Configuration file created: config.ini')
PYTHON_EOF
    fi
    
    # Create service directories if needed
    mkdir -p "$PROJECT_DIR/services/config"
    mkdir -p "$PROJECT_DIR/logs"
    
    print_header "Setup complete!"
    echo "    Virtual environment: $VENV_PATH"
    echo "    Configuration: $CONFIG_FILE"
    echo ""
    echo "Next steps:"
    echo "  1. Review and edit $CONFIG_FILE"
    echo "  2. Run a service: $0 run <service> <mode>"
}

do_run() {
    local service="$1"
    local mode="$2"
    
    if [ -z "$service" ] || [ -z "$mode" ]; then
        print_error "Both service and mode are required"
        usage
    fi
    
    # Validate mode
    if [ "$mode" != "stdio" ] && [ "$mode" != "sse" ]; then
        print_error "Invalid mode: $mode (must be 'stdio' or 'sse')"
        exit 1
    fi
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_PATH" ]; then
        print_error "Virtual environment not found. Run '$0 setup' first."
        exit 1
    fi
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    
    # Check if service exists
    SERVICE_SCRIPT="$PROJECT_DIR/services/mcp_${service}.py"
    if [ ! -f "$SERVICE_SCRIPT" ]; then
        print_warning "Service script not found: $SERVICE_SCRIPT"
        print_warning "Available services:"
        ls -1 "$PROJECT_DIR/services/" 2>/dev/null | grep "^mcp_.*\.py$" | sed 's/mcp_//;s/\.py//' || echo "  (none found)"
        exit 1
    fi
    
    # Load service-specific config if exists
    SERVICE_CONFIG="$PROJECT_DIR/services/config/${service}.ini"
    CONFIG_ARG=""
    if [ -f "$SERVICE_CONFIG" ]; then
        CONFIG_ARG="--config $SERVICE_CONFIG"
    fi
    
    # Only print status messages if not in stdio mode (to avoid interfering with JSON-RPC)
    if [ "$mode" != "stdio" ]; then
        print_header "Starting $service service in $mode mode..."
    fi
    
    # Add service-specific environment variables
    case "$service" in
        postgres)
            export DATABASE_URL="${DATABASE_URL:-postgresql://admin:Pass123qp@localhost:5432/postgres}"
            ;;
        github)
            if [ -f "$HOME/projects/secrets/github.env" ]; then
                source $HOME/projects/secrets/github.env
            fi
            ;;
        n8n)
            if [ -f "$HOME/projects/secrets/mcp-n8n.env" ]; then
                source $HOME/projects/secrets/mcp-n8n.env
            fi
            ;;
    esac
    
    # Activate virtual environment and run the service
    source "$VENV_PATH/bin/activate"
    python "$SERVICE_SCRIPT" --mode "$mode" $CONFIG_ARG
}

do_test() {
    local service="$1"
    
    print_header "Running test suite..."
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_PATH" ]; then
        print_error "Virtual environment not found. Run '$0 setup' first."
        exit 1
    fi
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    
    if [ -n "$service" ]; then
        # Test specific service
        print_header "Testing $service service..."
        pytest "$PROJECT_DIR/tests/test_${service}.py" -v --tb=short
    else
        # Run all tests
        pytest "$PROJECT_DIR/tests/" -v --tb=short
    fi
    
    # Run type checking
    print_header "Running type checks..."
    mypy "$PROJECT_DIR/services/" --ignore-missing-imports || print_warning "Type check warnings found"
    
    # Run code formatting check
    print_header "Checking code formatting..."
    black --check "$PROJECT_DIR/services/" "$PROJECT_DIR/tests/" || print_warning "Code formatting issues found (run 'black services/ tests/' to fix)"
}

do_clean() {
    print_header "Cleaning up..."
    
    # Remove virtual environment
    if [ -d "$VENV_PATH" ]; then
        print_header "Removing virtual environment..."
        rm -rf "$VENV_PATH"
        print_success "Virtual environment removed"
    fi
    
    # Remove Python cache
    print_header "Removing Python cache..."
    find "$PROJECT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
    print_success "Python cache removed"
    
    # Remove logs
    if [ -d "$PROJECT_DIR/logs" ]; then
        print_header "Removing logs..."
        rm -rf "$PROJECT_DIR/logs"
        print_success "Logs removed"
    fi
    
    print_success "Cleanup complete!"
}

do_status() {
    print_header "MCP Service Status"
    echo ""
    
    # Check virtual environment
    if [ -d "$VENV_PATH" ]; then
        print_success "Virtual environment exists"
    else
        print_warning "Virtual environment not found (run 'setup')"
    fi
    
    # Check services
    echo ""
    print_header "Available Services:"
    for service_file in "$PROJECT_DIR/services"/mcp_*.py; do
        if [ -f "$service_file" ]; then
            service_name=$(basename "$service_file" | sed 's/mcp_//;s/\.py//')
            config_file="$PROJECT_DIR/services/config/${service_name}.ini"
            if [ -f "$config_file" ]; then
                print_success "$service_name (configured)"
            else
                print_warning "$service_name (no config)"
            fi
        fi
    done
    
    # Check for running services (SSE mode)
    echo ""
    print_header "Running Services (SSE mode):"
    if lsof -i:8000-8100 2>/dev/null | grep -q LISTEN; then
        lsof -i:8000-8100 2>/dev/null | grep LISTEN | while read line; do
            port=$(echo "$line" | awk '{print $9}' | cut -d: -f2)
            echo "  Port $port is in use"
        done
    else
        echo "  (none detected)"
    fi
    
    # Check dependencies
    echo ""
    print_header "Dependencies:"
    if [ -d "$VENV_PATH" ]; then
        source "$VENV_PATH/bin/activate"
        pip_version=$(pip --version | awk '{print $2}')
        python_version=$(python --version | awk '{print $2}')
        print_success "Python $python_version"
        print_success "pip $pip_version"
        
        # Check critical packages
        for package in fastapi pydantic psycopg2-binary; do
            if pip show "$package" &>/dev/null; then
                version=$(pip show "$package" | grep Version | awk '{print $2}')
                print_success "$package $version"
            else
                print_warning "$package not installed"
            fi
        done
    fi
}

do_register() {
    local service="$1"
    
    if [ -z "$service" ]; then
        print_error "Service name is required"
        usage
    fi
    
    # Check if service exists
    SERVICE_SCRIPT="$PROJECT_DIR/services/mcp_${service}.py"
    if [ ! -f "$SERVICE_SCRIPT" ]; then
        print_error "Service script not found: $SERVICE_SCRIPT"
        print_warning "Available services:"
        ls -1 "$PROJECT_DIR/services/" 2>/dev/null | grep "^mcp_.*\.py$" | sed 's/mcp_//;s/\.py//' || echo "  (none found)"
        exit 1
    fi
    
    CLAUDE_CONFIG="/home/administrator/.claude/claude_desktop_config.json"
    
    print_header "Registering $service with Claude Code..."
    
    # Check if Claude config exists
    if [ ! -f "$CLAUDE_CONFIG" ]; then
        print_header "Creating new Claude Code configuration..."
        mkdir -p "$(dirname "$CLAUDE_CONFIG")"
        cat > "$CLAUDE_CONFIG" << 'EOF'
{
  "mcpServers": {}
}
EOF
    fi
    
    # Generate service configuration
    local service_key="${service}-v2"
    local command_path="$PROJECT_DIR/deploy.sh"
    
    # Get service-specific environment variables
    local env_vars=""
    case "$service" in
        postgres)
            env_vars='"DATABASE_URL": "postgresql://admin:Pass123qp@localhost:5432/postgres"'
            ;;
        github)
            if [ -f "$HOME/projects/secrets/github.env" ]; then
                # Extract GitHub token if available
                local github_token=$(grep "GITHUB_TOKEN=" $HOME/projects/secrets/github.env | cut -d'=' -f2 | tr -d '"')
                if [ -n "$github_token" ]; then
                    env_vars='"GITHUB_TOKEN": "'$github_token'"'
                fi
            fi
            ;;
        n8n)
            if [ -f "$HOME/projects/secrets/mcp-n8n.env" ]; then
                # Extract N8N credentials if available
                local n8n_host=$(grep "N8N_HOST=" $HOME/projects/secrets/mcp-n8n.env | cut -d'=' -f2 | tr -d '"')
                local n8n_token=$(grep "N8N_API_TOKEN=" $HOME/projects/secrets/mcp-n8n.env | cut -d'=' -f2 | tr -d '"')
                if [ -n "$n8n_host" ] && [ -n "$n8n_token" ]; then
                    env_vars='"N8N_HOST": "'$n8n_host'", "N8N_API_TOKEN": "'$n8n_token'"'
                fi
            fi
            ;;
    esac
    
    # Create Python script to update JSON safely
    cat > /tmp/update_mcp_config.py << 'PYTHON_EOF'
import json
import os
import sys

config_path = sys.argv[1]
service_key = sys.argv[2]
command_path = sys.argv[3]
service_name = sys.argv[4]
env_vars_str = sys.argv[5] if len(sys.argv) > 5 else ""

# Load existing config
try:
    with open(config_path, 'r') as f:
        config = json.load(f)
except:
    config = {"mcpServers": {}}

# Ensure mcpServers exists
if "mcpServers" not in config:
    config["mcpServers"] = {}

# Prepare environment variables
env_dict = {}
if env_vars_str:
    # Parse simple key-value pairs
    for pair in env_vars_str.split(", "):
        if ": " in pair:
            key = pair.split(": ")[0].strip('"')
            value = pair.split(": ")[1].strip('"')
            env_dict[key] = value

# Add/update service configuration
config["mcpServers"][service_key] = {
    "command": "bash",
    "args": ["-c", f"cd {command_path.rsplit('/', 1)[0]} && ./deploy.sh run {service_name} stdio"],
    "env": env_dict
}

# Write updated config
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print(f"✓ Service '{service_key}' registered successfully")
PYTHON_EOF
    
    # Run the Python script with arguments
    python3 /tmp/update_mcp_config.py "$CLAUDE_CONFIG" "$service_key" "$command_path" "$service" "$env_vars"
    
    print_success "Service registered with Claude Code"
    print_header "Configuration updated in: $CLAUDE_CONFIG"
    echo ""
    echo "Next steps:"
    echo "  1. Restart Claude Code to load the new configuration"
    echo "  2. Test with: /mcp in Claude Code"
    echo "  3. Run service: /home/administrator/projects/mcp/unified-registry-v2/deploy.sh run $service stdio"
}

do_register_all() {
    print_header "Registering all available services with Claude Code..."
    
    CLAUDE_CONFIG="/home/administrator/.claude/claude_desktop_config.json"
    
    # Check if Claude config exists, create if not
    if [ ! -f "$CLAUDE_CONFIG" ]; then
        print_header "Creating new Claude Code configuration..."
        mkdir -p "$(dirname "$CLAUDE_CONFIG")"
        cat > "$CLAUDE_CONFIG" << 'EOF'
{
  "mcpServers": {}
}
EOF
    fi
    
    # Find all available services
    local services_found=()
    for service_file in "$PROJECT_DIR/services"/mcp_*.py; do
        if [ -f "$service_file" ]; then
            service_name=$(basename "$service_file" | sed 's/mcp_//;s/\.py//')
            services_found+=("$service_name")
        fi
    done
    
    if [ ${#services_found[@]} -eq 0 ]; then
        print_warning "No MCP services found in $PROJECT_DIR/services/"
        return
    fi
    
    print_header "Found ${#services_found[@]} services: ${services_found[*]}"
    echo ""
    
    # Register each service
    for service in "${services_found[@]}"; do
        print_header "Registering $service..."
        
        # Register the service (reuse logic from do_register)
        local service_key="${service}-v2"
        local command_path="$PROJECT_DIR/deploy.sh"
        
        # Get service-specific environment variables
        local env_vars=""
        case "$service" in
            postgres)
                env_vars='"DATABASE_URL": "postgresql://admin:Pass123qp@localhost:5432/postgres"'
                ;;
            github)
                if [ -f "$HOME/projects/secrets/github.env" ]; then
                    local github_token=$(grep "GITHUB_TOKEN=" $HOME/projects/secrets/github.env | cut -d'=' -f2 | tr -d '"')
                    if [ -n "$github_token" ]; then
                        env_vars='"GITHUB_TOKEN": "'$github_token'"'
                    fi
                fi
                ;;
            n8n)
                if [ -f "$HOME/projects/secrets/mcp-n8n.env" ]; then
                    local n8n_host=$(grep "N8N_HOST=" $HOME/projects/secrets/mcp-n8n.env | cut -d'=' -f2 | tr -d '"')
                    local n8n_token=$(grep "N8N_API_TOKEN=" $HOME/projects/secrets/mcp-n8n.env | cut -d'=' -f2 | tr -d '"')
                    if [ -n "$n8n_host" ] && [ -n "$n8n_token" ]; then
                        env_vars='"N8N_HOST": "'$n8n_host'", "N8N_API_TOKEN": "'$n8n_token'"'
                    fi
                fi
                ;;
        esac
        
        # Update config using Python
        python3 /tmp/update_mcp_config.py "$CLAUDE_CONFIG" "$service_key" "$command_path" "$service" "$env_vars"
        
        print_success "$service registered"
    done
    
    echo ""
    print_success "All services registered with Claude Code"
    print_header "Configuration updated in: $CLAUDE_CONFIG"
    echo ""
    echo "Next steps:"
    echo "  1. Restart Claude Code to load the new configuration"
    echo "  2. Test with: /mcp in Claude Code"
    echo "  3. All services will be available as: ${services_found[*]/%/-v2}"
}

# Main logic
cd "$PROJECT_DIR"

case "$1" in
    setup)
        do_setup
        ;;
    run)
        do_run "$2" "$3"
        ;;
    test)
        do_test "$2"
        ;;
    clean)
        do_clean
        ;;
    status)
        do_status
        ;;
    register)
        do_register "$2"
        ;;
    register-all)
        do_register_all
        ;;
    *)
        usage
        ;;
esac