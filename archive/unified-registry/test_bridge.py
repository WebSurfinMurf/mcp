#!/usr/bin/env python3
"""
Test script to validate the tool bridge works with MCP services
"""

import asyncio
import json
from tool_definitions import TOOL_DEFINITIONS, find_tool
from tool_bridge import MCPToolBridge

async def test_filesystem_direct():
    """Test filesystem service via direct Docker execution"""
    print("\n=== Testing Filesystem Service (Direct Docker) ===")
    
    service_def = TOOL_DEFINITIONS["filesystem"]
    bridge = MCPToolBridge(use_sse_proxy=False)
    
    # First, list available tools
    print("Listing tools...")
    result = bridge.list_tools_docker(service_def["docker_command"])
    if result["success"]:
        print(f"Found {len(result['tools'])} tools")
        for tool in result["tools"][:3]:  # Show first 3
            print(f"  - {tool.get('name', 'unknown')}")
    else:
        print(f"Error listing tools: {result['error']}")
        return False
    
    # Test list_directory
    print("\nTesting list_directory on /home/administrator/projects/mcp...")
    result = await bridge.execute_tool(
        service="filesystem",
        endpoint=service_def["endpoint"],
        docker_command=service_def["docker_command"],
        tool_name="list_directory",
        params={"path": "/home/administrator/projects/mcp"}
    )
    
    if result["success"]:
        print("✓ list_directory successful")
        data = result["data"]
        if isinstance(data, list) and len(data) > 0:
            print(f"  Found {len(data)} items")
            for item in data[:5]:  # Show first 5
                if isinstance(item, dict):
                    print(f"    - {item.get('name', 'unknown')}")
        return True
    else:
        print(f"✗ list_directory failed: {result['error']}")
        return False

async def test_postgres_direct():
    """Test postgres service via direct Docker execution"""
    print("\n=== Testing PostgreSQL Service (Direct Docker) ===")
    
    service_def = TOOL_DEFINITIONS["postgres"]
    bridge = MCPToolBridge(use_sse_proxy=False)
    
    # List available tools
    print("Listing tools...")
    result = bridge.list_tools_docker(service_def["docker_command"])
    if result["success"]:
        print(f"Found {len(result['tools'])} tools")
        for tool in result["tools"][:3]:  # Show first 3
            print(f"  - {tool.get('name', 'unknown')}")
    else:
        print(f"Error listing tools: {result['error']}")
        return False
    
    # Test list_databases
    print("\nTesting list_databases...")
    result = await bridge.execute_tool(
        service="postgres",
        endpoint=service_def["endpoint"],
        docker_command=service_def["docker_command"],
        tool_name="list_databases",
        params={}
    )
    
    if result["success"]:
        print("✓ list_databases successful")
        data = result["data"]
        if isinstance(data, list):
            print(f"  Found {len(data)} databases")
            for db in data[:5]:  # Show first 5
                if isinstance(db, dict):
                    print(f"    - {db.get('name', 'unknown')}")
        return True
    else:
        print(f"✗ list_databases failed: {result['error']}")
        return False

async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing MCP Tool Bridge")
    print("=" * 60)
    
    # Test filesystem
    fs_success = await test_filesystem_direct()
    
    # Test postgres
    pg_success = await test_postgres_direct()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print(f"  Filesystem: {'✓ PASS' if fs_success else '✗ FAIL'}")
    print(f"  PostgreSQL: {'✓ PASS' if pg_success else '✗ FAIL'}")
    print("=" * 60)
    
    return fs_success and pg_success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)