#!/usr/bin/env python3
"""
Direct stdio runner for MCP Code Executor
Runs code-executor in stdio mode for Claude CLI integration
"""
import subprocess
import sys
import os

def main():
    """Run code-executor MCP server in stdio mode"""
    try:
        # Run docker exec with stdio passthrough
        cmd = [
            'docker',
            'exec',
            '-i',
            'mcp-code-executor',
            'npx',
            'tsx',
            '/app/mcp-server.ts'
        ]

        # Execute with stdio passthrough (same pattern as postgres-mcp-stdio.py)
        process = subprocess.Popen(
            cmd,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True
        )

        # Wait for completion
        process.wait()
        return process.returncode

    except Exception as e:
        print(f"Error running code-executor: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
