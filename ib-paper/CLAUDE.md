# MCP IB Paper Trading Server

## Overview
MCP server for Interactive Brokers paper trading. Used by websurfinmurf/model environment.

## Quick Reference
| Property | Value |
|----------|-------|
| Container | mcp-ib-paper |
| Gateway | mcp-ib-gateway-paper |
| HTTP Port | 48012 |
| Gateway Ports | 14001 (live), 14002 (paper), 15900 (VNC) |
| Network | mcp-ib-paper-net |
| MCP Endpoint | http://localhost:48012/mcp |
| Owner | websurfinmurf |

## Configuration
- **Trading Mode**: Paper (always)
- **IB Port**: 4004 (paper socat)
- **Client ID**: 1

## Secrets
Location: `$HOME/projects/secrets/mcp-ib-paper.env`

## Common Commands
```bash
# Deploy
cd /home/administrator/projects/mcp/ib-paper && ./deploy.sh

# Logs
docker logs mcp-ib-paper --tail 50
docker logs mcp-ib-gateway-paper --tail 50

# Health check
curl http://localhost:48012/health

# Test MCP call
curl -X POST http://localhost:48012/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"get_account_summary","arguments":{}}}'
```

## Related
- **Live Server**: `/home/administrator/projects/mcp/ib-live/`
- **Original Setup**: `/home/administrator/projects/mcp/ib/`

---
*Last Updated: 2025-12-02*
