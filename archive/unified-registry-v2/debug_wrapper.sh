#!/bin/bash
# Debug wrapper for MCP postgres service
# Logs all input/output for diagnostics

LOG_DIR="/home/administrator/projects/mcp/unified-registry-v2/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/mcp_debug_$(date +%Y%m%d_%H%M%S).log"
TIMING_FILE="$LOG_DIR/mcp_timing_$(date +%Y%m%d_%H%M%S).log"

echo "=== MCP Debug Session Started: $(date) ===" >> "$LOG_FILE"
echo "Command: $0 $@" >> "$LOG_FILE"
echo "Environment:" >> "$LOG_FILE"
env | grep -E "DATABASE|PATH|PYTHON" >> "$LOG_FILE"
echo "Working Directory: $(pwd)" >> "$LOG_FILE"
echo "===========================================" >> "$LOG_FILE"

# Create a named pipe for capturing both stdin and stdout
PIPE_DIR="/tmp/mcp_debug_$$"
mkdir -p "$PIPE_DIR"
STDIN_PIPE="$PIPE_DIR/stdin"
STDOUT_PIPE="$PIPE_DIR/stdout"
mkfifo "$STDIN_PIPE" "$STDOUT_PIPE"

# Function to log with timestamp
log_msg() {
    echo "[$(date +%H:%M:%S.%3N)] $1" >> "$LOG_FILE"
}

# Function to log timing
log_timing() {
    echo "[$(date +%H:%M:%S.%3N)] $1" >> "$TIMING_FILE"
}

log_msg "Starting MCP service..."
log_timing "START"

# Start the actual service in background, capturing all I/O
(
    cd /home/administrator/projects/mcp/unified-registry-v2
    export PYTHONUNBUFFERED=1
    export MCP_DEBUG=1
    
    # Log stdin
    tee -a "$LOG_FILE" < "$STDIN_PIPE" | \
    # Run the service
    ./deploy.sh run postgres stdio 2>>"$LOG_FILE" | \
    # Log stdout
    tee -a "$LOG_FILE" > "$STDOUT_PIPE"
) &

SERVICE_PID=$!
log_msg "Service started with PID: $SERVICE_PID"

# Forward stdin to the pipe
cat > "$STDIN_PIPE" &
CAT_PID=$!

# Forward stdout from the pipe
cat < "$STDOUT_PIPE"

# Wait for service to finish
wait $SERVICE_PID
EXIT_CODE=$?

log_timing "END (exit code: $EXIT_CODE)"
log_msg "Service exited with code: $EXIT_CODE"

# Cleanup
kill $CAT_PID 2>/dev/null || true
rm -rf "$PIPE_DIR"

echo "=== MCP Debug Session Ended: $(date) ===" >> "$LOG_FILE"
echo "Debug log saved to: $LOG_FILE" >&2

exit $EXIT_CODE