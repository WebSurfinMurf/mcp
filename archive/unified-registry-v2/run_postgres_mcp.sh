#!/bin/bash
# Simple wrapper for Claude Code MCP integration
# This ensures proper environment setup

# Set working directory
cd /home/administrator/projects/mcp/unified-registry-v2 || exit 1

# Set environment
export DATABASE_URL="${DATABASE_URL:-postgresql://admin:Pass123qp@localhost:5432/postgres}"
export PYTHONUNBUFFERED=1

# Activate virtual environment and run
source venv/bin/activate 2>/dev/null || true
exec python3 services/mcp_postgres.py --mode stdio