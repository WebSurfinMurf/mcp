#!/usr/bin/env python3
"""
Direct test of MCP services using Docker commands
"""

import subprocess
import json

def test_filesystem():
    """Test filesystem service directly"""
    print("\n=== Testing Filesystem Service ===")
    
    # Prepare JSON-RPC requests
    requests = [
        {"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1},
        {"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}
    ]
    
    input_data = "\n".join(json.dumps(r) for r in requests)
    
    # Run Docker command
    cmd = [
        "docker", "run", "--rm", "-i",
        "-v", "/home/administrator:/workspace:ro",
        "mcp/filesystem", "/workspace"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Parse output
        lines = result.stdout.strip().split('\n')
        for line in lines:
            try:
                response = json.loads(line)
                if response.get("id") == 2:
                    tools = response.get("result", {}).get("tools", [])
                    print(f"✓ Found {len(tools)} tools")
                    for tool in tools[:3]:
                        print(f"  - {tool['name']}")
                    return True
            except json.JSONDecodeError:
                continue
                
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    return False

def test_postgres():
    """Test postgres service directly"""
    print("\n=== Testing PostgreSQL Service ===")
    
    # Prepare JSON-RPC requests
    requests = [
        {"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1},
        {"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}
    ]
    
    input_data = "\n".join(json.dumps(r) for r in requests)
    
    # Run Docker command
    cmd = [
        "docker", "run", "--rm", "-i",
        "--network", "postgres-net",
        "-e", "DATABASE_URI=postgresql://admin:Pass123qp@postgres:5432/postgres",
        "crystaldba/postgres-mcp"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Parse output
        lines = result.stdout.strip().split('\n')
        for line in lines:
            try:
                response = json.loads(line)
                if response.get("id") == 2:
                    tools = response.get("result", {}).get("tools", [])
                    print(f"✓ Found {len(tools)} tools")
                    for tool in tools[:3]:
                        print(f"  - {tool['name']}")
                    return True
            except json.JSONDecodeError:
                continue
                
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    return False

def test_tool_execution():
    """Test actual tool execution"""
    print("\n=== Testing Tool Execution ===")
    
    # Test filesystem list_directory
    requests = [
        {"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1},
        {"jsonrpc":"2.0","method":"tools/call","params":{"name":"list_directory","arguments":{"path":"/workspace/projects/mcp"}},"id":2}
    ]
    
    input_data = "\n".join(json.dumps(r) for r in requests)
    
    cmd = [
        "docker", "run", "--rm", "-i",
        "-v", "/home/administrator:/workspace:ro",
        "mcp/filesystem", "/workspace"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Parse output
        lines = result.stdout.strip().split('\n')
        for line in lines:
            try:
                response = json.loads(line)
                if response.get("id") == 2:
                    if "result" in response:
                        content = response["result"].get("content", [])
                        if content and len(content) > 0:
                            text = content[0].get("text", "")
                            # Count directories
                            dir_count = text.count("[DIR]")
                            file_count = text.count("[FILE]")
                            print(f"✓ list_directory succeeded: {dir_count} dirs, {file_count} files")
                            return True
            except json.JSONDecodeError:
                continue
                
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    return False

if __name__ == "__main__":
    print("=" * 60)
    print("Direct MCP Service Testing")
    print("=" * 60)
    
    fs_ok = test_filesystem()
    pg_ok = test_postgres()
    exec_ok = test_tool_execution()
    
    print("\n" + "=" * 60)
    print("Results:")
    print(f"  Filesystem Service: {'✓ PASS' if fs_ok else '✗ FAIL'}")
    print(f"  PostgreSQL Service: {'✓ PASS' if pg_ok else '✗ FAIL'}")
    print(f"  Tool Execution: {'✓ PASS' if exec_ok else '✗ FAIL'}")
    print("=" * 60)