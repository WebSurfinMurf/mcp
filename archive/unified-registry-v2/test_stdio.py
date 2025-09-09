#!/usr/bin/env python3
"""
Test script for PostgreSQL MCP service in stdio mode
"""

import json
import subprocess
import sys
import os


def send_request(process, request):
    """Send a JSON-RPC request and get response"""
    request_str = json.dumps(request)
    print(f"→ Sending: {request_str}", file=sys.stderr)
    
    process.stdin.write(request_str + "\n")
    process.stdin.flush()
    
    response_line = process.stdout.readline()
    if response_line:
        response = json.loads(response_line)
        print(f"← Response: {json.dumps(response, indent=2)}", file=sys.stderr)
        return response
    return None


def test_postgres_stdio():
    """Test PostgreSQL service in stdio mode"""
    print("Testing PostgreSQL MCP Service in stdio mode...\n", file=sys.stderr)
    
    # Set environment for database connection
    env = os.environ.copy()
    env['DATABASE_URL'] = 'postgresql://admin:Pass123qp@localhost:5432/postgres'
    
    # Start the service in stdio mode
    process = subprocess.Popen(
        [sys.executable, "services/mcp_postgres.py", "--mode", "stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd="/home/administrator/projects/mcp/unified-registry-v2"
    )
    
    try:
        # Test 1: Initialize
        print("\n=== Test 1: Initialize ===", file=sys.stderr)
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test_client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }
        response = send_request(process, init_request)
        assert response and "result" in response, "Initialize failed"
        print("✓ Initialize successful", file=sys.stderr)
        
        # Test 2: List tools
        print("\n=== Test 2: List Tools ===", file=sys.stderr)
        list_tools_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }
        response = send_request(process, list_tools_request)
        assert response and "result" in response, "List tools failed"
        tools = response["result"]["tools"]
        print(f"✓ Found {len(tools)} tools:", file=sys.stderr)
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}", file=sys.stderr)
        
        # Test 3: List databases
        print("\n=== Test 3: List Databases ===", file=sys.stderr)
        list_db_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "list_databases",
                "arguments": {
                    "include_system": False,
                    "include_size": True
                }
            },
            "id": 3
        }
        response = send_request(process, list_db_request)
        if response and "result" in response:
            print("✓ List databases successful", file=sys.stderr)
            # Parse the result content
            content = response["result"]["content"][0]["text"]
            db_data = json.loads(content)
            print(f"  Found {db_data['count']} databases", file=sys.stderr)
        else:
            print("✗ List databases failed", file=sys.stderr)
        
        # Test 4: Execute a simple SELECT query
        print("\n=== Test 4: Execute SELECT Query ===", file=sys.stderr)
        query_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "execute_sql",
                "arguments": {
                    "query": "SELECT version(), current_database(), current_user",
                    "format": "json"
                }
            },
            "id": 4
        }
        response = send_request(process, query_request)
        if response and "result" in response:
            print("✓ Query execution successful", file=sys.stderr)
        else:
            print("✗ Query execution failed", file=sys.stderr)
        
        # Test 5: Invalid tool call (should return error)
        print("\n=== Test 5: Invalid Tool Call ===", file=sys.stderr)
        invalid_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "nonexistent_tool",
                "arguments": {}
            },
            "id": 5
        }
        response = send_request(process, invalid_request)
        if response and "error" in response:
            print(f"✓ Error handling works: {response['error']['message']}", file=sys.stderr)
        else:
            print("✗ Error handling failed", file=sys.stderr)
        
        # Test 6: Validation error (invalid parameters)
        print("\n=== Test 6: Parameter Validation ===", file=sys.stderr)
        invalid_params_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "execute_sql",
                "arguments": {
                    "query": "",  # Empty query should fail validation
                    "timeout": 1000  # Too high timeout
                }
            },
            "id": 6
        }
        response = send_request(process, invalid_params_request)
        if response and "error" in response:
            print(f"✓ Validation works: {response['error']['message']}", file=sys.stderr)
        else:
            print("✗ Validation failed", file=sys.stderr)
        
        print("\n=== All Tests Complete ===", file=sys.stderr)
        
    finally:
        # Clean up
        process.terminate()
        process.wait()


if __name__ == "__main__":
    test_postgres_stdio()