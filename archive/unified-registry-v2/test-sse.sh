#!/bin/bash
# Manual SSE mode testing

echo "Testing PostgreSQL v2 SSE Mode"
echo "=============================="

# Test 1: List databases via RPC
echo ""
echo "Test 1: List databases"
echo "----------------------"
curl -X POST http://localhost:8001/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "list_databases",
      "arguments": {
        "include_system": false,
        "include_size": true
      }
    },
    "id": 1
  }' | jq .

# Test 2: Execute SQL
echo ""
echo "Test 2: Execute SQL query"
echo "-------------------------"
curl -X POST http://localhost:8001/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "execute_sql",
      "arguments": {
        "query": "SELECT version(), current_user",
        "format": "json"
      }
    },
    "id": 2
  }' | jq .

# Test 3: Error handling
echo ""
echo "Test 3: Error handling (forbidden operation)"
echo "--------------------------------------------"
curl -X POST http://localhost:8001/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "execute_sql",
      "arguments": {
        "query": "DROP TABLE test",
        "format": "json"
      }
    },
    "id": 3
  }' | jq .