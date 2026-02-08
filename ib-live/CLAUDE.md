# MCP IB Live Trading Server

## Overview
MCP server for Interactive Brokers live trading. Used by administrator/production environment.

**WARNING**: Currently configured for PAPER trading mode for testing. See "Switching to Live" below.

## Quick Reference
| Property | Value |
|----------|-------|
| Container | mcp-ib-live |
| Gateway | mcp-ib-gateway-live |
| HTTP Port | 48014 |
| Gateway Ports | 14011 (live), 14012 (paper), 15901 (VNC) |
| Network | mcp-ib-live-net |
| MCP Endpoint | http://localhost:48014/mcp |
| Owner | administrator |

## Configuration
- **Trading Mode**: Paper (currently, for testing)
- **IB Port**: 4004 (paper socat) - change to 4003 for live
- **Client ID**: 10

## Secrets
Location: `$HOME/projects/secrets/mcp-ib-live.env`

## Switching to Live Trading

**WARNING**: This will use REAL MONEY. Double-check everything.

1. Update `$HOME/projects/secrets/mcp-ib-live.env`:
   ```bash
   TRADING_MODE=live
   IB_PORT=4003
   ```

2. Update `docker-compose.yml`:
   - Change `IB_PORT: 4004` to `IB_PORT: 4003`
   - Change `TRADING_MODE: paper` to `TRADING_MODE: live`

3. Redeploy:
   ```bash
   docker compose down
   ./deploy.sh
   ```

## Common Commands
```bash
# Deploy
cd /home/administrator/projects/mcp/ib-live && ./deploy.sh

# Logs
docker logs mcp-ib-live --tail 50
docker logs mcp-ib-gateway-live --tail 50

# Health check
curl http://localhost:48014/health

# Test MCP call
curl -X POST http://localhost:48014/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"get_account_summary","arguments":{}}}'
```

## Related
- **Paper Server**: `/home/administrator/projects/mcp/ib-paper/`
- **Original Setup**: `/home/administrator/projects/mcp/ib/`

---
*Last Updated: 2025-12-02*
