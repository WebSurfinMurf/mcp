#!/bin/bash
# MCP Dual-Mode Deployment Script
# Manages Python virtual environment and service deployment

set -e

# Configuration
PROJECT_NAME="mcp-dualdeploy"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$PROJECT_DIR/venv"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_status() {
    echo -e "${GREEN}==>${NC} $1"
}

print_error() {
    echo -e "${RED}ERROR:${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

usage() {
    echo "MCP Dual-Mode Deployment Script"
    echo "--------------------------------"
    echo "Usage: $0 {setup|run|test|register|status|clean}"
    echo ""
    echo "Commands:"
    echo "  setup              Create virtual environment and install dependencies"
    echo "  run <service> <mode>  Run a service (mode: stdio|sse)"
    echo "  test <service>     Test a service in stdio mode"
    echo "  register <service> Register service with Claude Code"
    echo "  status             Check service status"
    echo "  clean              Remove virtual environment and cache"
    exit 1
}

do_setup() {
    print_status "Setting up MCP environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$VENV_PATH" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv "$VENV_PATH" || {
            print_warning "venv module not found, installing pip directly..."
            curl -s https://bootstrap.pypa.io/get-pip.py | python3 - --user
            python3 -m venv "$VENV_PATH"
        }
    fi
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    
    # Upgrade pip
    print_status "Upgrading pip..."
    pip install --upgrade pip >/dev/null 2>&1
    
    # Install dependencies
    if [ -f "$REQUIREMENTS_FILE" ]; then
        print_status "Installing dependencies..."
        pip install -r "$REQUIREMENTS_FILE"
    fi
    
    print_status "Setup complete!"
    echo ""
    echo "Virtual environment: $VENV_PATH"
    echo "Next step: $0 run postgres stdio"
}

do_run() {
    local service="$1"
    local mode="$2"
    
    if [ -z "$service" ] || [ -z "$mode" ]; then
        print_error "Both service and mode are required"
        usage
    fi
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_PATH" ]; then
        print_error "Virtual environment not found. Run '$0 setup' first."
        exit 1
    fi
    
    # Service script path
    SERVICE_SCRIPT="$PROJECT_DIR/services/mcp_${service}.py"
    if [ ! -f "$SERVICE_SCRIPT" ]; then
        print_error "Service not found: $service"
        exit 1
    fi
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    
    # Set environment variables
    export DATABASE_URL="${DATABASE_URL:-postgresql://admin:Pass123qp@localhost:5432/postgres}"
    export PYTHONUNBUFFERED=1
    
    # Run the service
    if [ "$mode" = "stdio" ]; then
        print_status "Starting $service in stdio mode..."
        exec python "$SERVICE_SCRIPT" --mode stdio
    elif [ "$mode" = "sse" ]; then
        print_status "Starting $service in SSE mode on port 8001..."
        exec python "$SERVICE_SCRIPT" --mode sse --port 8001
    else
        print_error "Invalid mode: $mode (use stdio or sse)"
        exit 1
    fi
}

do_test() {
    local service="$1"
    
    if [ -z "$service" ]; then
        print_error "Service name required"
        usage
    fi
    
    print_status "Testing $service service..."
    
    # Test with simple tools/list request
    echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1}' | \
        "$PROJECT_DIR/deploy.sh" run "$service" stdio | head -1
    
    echo '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}' | \
        "$PROJECT_DIR/deploy.sh" run "$service" stdio | head -1
}

do_register() {
    local service="$1"
    
    if [ -z "$service" ]; then
        print_error "Service name required"
        usage
    fi
    
    # Claude Code configuration file
    CONFIG_FILE="$HOME/.config/claude/mcp-settings.json"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "Claude Code configuration not found at $CONFIG_FILE"
        exit 1
    fi
    
    print_status "Registering $service with Claude Code..."
    
    # Use Python to safely update JSON
    python3 << EOF
import json
import os

config_file = "$CONFIG_FILE"
service_name = "${service}-v2"
shim_path = "$PROJECT_DIR/shims/${service}.js"

# Read existing config
with open(config_file, 'r') as f:
    config = json.load(f)

# Update with new service
if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers'][service_name] = {
    "command": shim_path,
    "args": []
}

# Write back
with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)

print(f"✓ Registered {service_name} in Claude Code configuration")
print(f"  Shim: {shim_path}")
print(f"  Config: {config_file}")
print("")
print("Restart Claude Code to activate the service.")
EOF
}

do_status() {
    print_status "MCP Dual-Deploy Status"
    echo ""
    
    # Check virtual environment
    if [ -d "$VENV_PATH" ]; then
        echo "✓ Virtual environment exists"
    else
        echo "✗ Virtual environment not found (run setup)"
    fi
    
    # Check services
    echo ""
    echo "Available services:"
    for service_file in "$PROJECT_DIR/services"/mcp_*.py; do
        if [ -f "$service_file" ]; then
            service_name=$(basename "$service_file" | sed 's/mcp_//;s/.py//')
            echo "  - $service_name"
        fi
    done
    
    # Check shims
    echo ""
    echo "Available shims:"
    for shim_file in "$PROJECT_DIR/shims"/*.js; do
        if [ -f "$shim_file" ]; then
            shim_name=$(basename "$shim_file" .js)
            echo "  - $shim_name"
        fi
    done
}

do_clean() {
    print_status "Cleaning up..."
    
    # Remove virtual environment
    if [ -d "$VENV_PATH" ]; then
        print_status "Removing virtual environment..."
        rm -rf "$VENV_PATH"
    fi
    
    # Remove Python cache
    print_status "Removing Python cache..."
    find "$PROJECT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
    
    print_status "Cleanup complete!"
}

# Main logic
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
    register)
        do_register "$2"
        ;;
    status)
        do_status
        ;;
    clean)
        do_clean
        ;;
    *)
        usage
        ;;
esac