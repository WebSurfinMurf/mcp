#!/usr/bin/env python3
"""
Direct stdio runner for crystaldba/postgres-mcp
Runs postgres-mcp in stdio mode for Codex CLI integration
"""
import subprocess
import sys
import os

# Database connection from environment or default to main postgres
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://admin:Pass123qp@localhost:5432/postgres')

def main():
    """Run postgres-mcp in stdio mode"""
    try:
        # Run postgres-mcp with stdio transport
        cmd = [
            'postgres-mcp',
            '--transport', 'stdio',
            '--access-mode', 'restricted',
            DATABASE_URL
        ]

        # Set environment to customize server name
        env = os.environ.copy()
        env['POSTGRES_MCP_SERVER_NAME'] = 'PostgreSQL-Main'

        # Execute with stdio passthrough
        process = subprocess.Popen(
            cmd,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True,
            env=env
        )

        # Wait for completion
        process.wait()
        return process.returncode

    except Exception as e:
        print(f"Error running postgres-mcp: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())