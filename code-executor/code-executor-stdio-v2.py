#!/usr/bin/env python3
"""
MCP stdio bridge for code-executor
Pipes stdin/stdout through to docker exec in an interactive loop
Based on the working mcp-bridge.py pattern
"""
import subprocess
import sys
import threading
import queue

def main():
    """Run docker exec with bidirectional stdio piping"""
    # Start docker exec with stdin pipe
    process = subprocess.Popen(
        [
            'docker',
            'exec',
            '-i',  # Keep stdin open
            'mcp-code-executor',
            'npx',
            'tsx',
            '/app/mcp-server.ts'
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,  # Errors to stderr
        text=True,
        bufsize=1  # Line buffered
    )

    def read_stdout():
        """Read from docker stdout and write to our stdout"""
        try:
            for line in process.stdout:
                print(line, end='', flush=True)
        except:
            pass

    # Start thread to read docker stdout
    stdout_thread = threading.Thread(target=read_stdout, daemon=True)
    stdout_thread.start()

    # Read from our stdin and write to docker stdin
    try:
        for line in sys.stdin:
            process.stdin.write(line)
            process.stdin.flush()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        process.stdin.close()
        process.wait()

if __name__ == "__main__":
    main()
