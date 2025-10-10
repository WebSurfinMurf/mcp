# Interactive Brokers MCP Server

## 📋 Project Overview
MCP server providing Interactive Brokers market data and portfolio operations through TWS API. Deployed with IB Gateway in paper trading mode, accessible via HTTP wrapper for MCP protocol compatibility.

## 🟢 Current State (2025-10-10)
- **Status**: ✅ Operational - Paper trading account connected
- **IB Gateway Version**: 10.40.1c (October 7, 2025)
- **ib-mcp Version**: 0.2.9 (latest)
- **Account**: DUO062910 (Paper Trading, $1,000,592.65 equity)
- **HTTP Endpoint**: `http://localhost:48012/mcp`
- **Proxy Endpoint**: `http://localhost:9090/ib/mcp`
- **Total Tools**: 10 market data and portfolio operations

## 📝 Recent Work & Changes

### Session: 2025-10-10 - Initial Deployment Complete
- **Issue Discovered**: TrustedIPs configuration doesn't work in IB Gateway
- **Root Cause**: Gateway only listens on 127.0.0.1, regardless of TrustedIPs setting
- **Solution**: gnzsnz/ib-gateway image uses `socat` to proxy API ports
  - Port 4002 (internal, paper trading) → Port 4004 (external via socat)
  - Port 4001 (internal, live trading) → Port 4003 (external via socat)
- **Configuration**: Updated IB_PORT from 4002 to 4004 in mcp-ib.env
- **Gateway Update**: Updated to latest image (10.40.1c from 10.40.1b)
- **Architecture**: FastAPI HTTP wrapper around ib-mcp STDIO server
- **Network**: Added network alias "ibgateway" for mcp-ib-gateway container

## 🏗️ Architecture

```
Claude Code / Kilo Code
        │ (HTTP)
        ▼
TBXark Proxy (localhost:9090/ib/mcp)
        │ (HTTP)
        ▼
MCP IB HTTP Server (mcp-ib:8000/mcp)
        │ (STDIO)
        ▼
ib-mcp subprocess (python3 -m ib_mcp.server)
        │ (IB TWS API)
        ▼
socat (port 4004 → 127.0.0.1:4002)
        │
        ▼
IB Gateway (mcp-ib-gateway)
        │ (HTTPS)
        ▼
Interactive Brokers Cloud (paper trading)
```

### Network Configuration
- **mcp-ib-net**: Internal network for MCP ↔ Gateway communication
  - Container: mcp-ib (172.20.0.3)
  - Container: mcp-ib-gateway (172.20.0.2) - alias: ibgateway
- **mcp-net**: External network for proxy access

### Critical Discovery: socat Port Mapping
The IB Gateway Docker image uses `socat` to work around TrustedIPs limitations:
- **Paper Trading API**: Internal 127.0.0.1:4002 → External 0.0.0.0:4004
- **Live Trading API**: Internal 127.0.0.1:4001 → External 0.0.0.0:4003

**IMPORTANT**: Always connect to port 4004 (paper) or 4003 (live), NOT the standard 4002/4001 ports!

## ⚙️ Configuration

### Files
- **Docker Compose**: `/home/administrator/projects/mcp/ib/docker-compose.yml`
- **Credentials**: `/home/administrator/projects/secrets/mcp-ib.env` ⚠️ CONFIDENTIAL
- **HTTP Server**: `/home/administrator/projects/mcp/ib/src/server.py`
- **Proxy Wrapper**: `/home/administrator/projects/mcp/proxy/wrappers/ib-wrapper.sh`
- **Dockerfile**: `/home/administrator/projects/mcp/ib/Dockerfile`

### Environment Variables (mcp-ib.env)
```bash
# IB Gateway credentials
IB_USERNAME=<paper_trading_username>
IB_PASSWORD=<password>
TRADING_MODE=paper
READ_ONLY_API=no
VNC_PASSWORD=<vnc_password>
VNC_SERVER_PASSWORD=<vnc_password>

# MCP Server Configuration
IB_HOST=ibgateway
IB_PORT=4004          # ← socat proxy port, NOT 4002!
IB_CLIENT_ID=1
IB_READONLY=true

# Two-factor authentication
TWOFA_TIMEOUT_ACTION=restart
```

### Docker Compose Services

**mcp-ib** (HTTP wrapper):
- Image: Custom build (Python 3.12 + ib-mcp + FastAPI)
- Port: 48012:8000
- Networks: mcp-ib-net, mcp-net
- Health check: HTTP GET /health

**mcp-ib-gateway** (IB Gateway):
- Image: ghcr.io/gnzsnz/ib-gateway:latest
- Ports:
  - 14001:4001 (live trading API via socat → 4003)
  - 14002:4002 (paper trading API via socat → 4004)
  - 15900:5900 (VNC server)
- Volumes:
  - ./jts:/root/Jts (Gateway settings)
  - ./ibc:/root/ibc (IBC automation config)

## 🌐 Access & Management

### Service Endpoints
- **Direct HTTP**: `http://localhost:48012/mcp`
- **Via Proxy**: `http://localhost:9090/ib/mcp`
- **Health Check**: `http://localhost:48012/health`
- **VNC Access**: `vnc://localhost:15900` (password in mcp-ib.env)

### Available Tools (10 total)
1. **get_account_summary** - Retrieve account information
2. **get_article** - Fetch news articles by ID
3. **get_contract_details** - Detailed contract specifications
4. **get_fundamental_data** - Company fundamental data
5. **get_historical_data** - Historical price data (OHLCV)
6. **get_historical_news** - Historical news headlines
7. **get_positions** - Current portfolio positions
8. **lookup_contract** - Find contracts by symbol
9. **search_contracts** - Search for contracts by pattern
10. **ticker_to_conid** - Convert ticker to contract ID

### Testing Tools

#### Via Direct HTTP
```bash
curl -X POST http://localhost:48012/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tools/call",
    "params": {
      "name": "get_account_summary",
      "arguments": {}
    }
  }'
```

#### Via Proxy
```bash
curl -X POST http://localhost:9090/ib/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tools/list",
    "params": {}
  }'
```

#### Get Historical Data
```bash
curl -X POST http://localhost:48012/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "tools/call",
    "params": {
      "name": "get_historical_data",
      "arguments": {
        "symbol": "AAPL",
        "duration": "1 M",
        "bar_size": "1 day"
      }
    }
  }'
```

## 🔗 Integration Points

### TBXark MCP Proxy
Added to `/home/administrator/projects/mcp/proxy/config.json`:
```json
{
  "mcpServers": {
    "ib": {
      "command": "/wrappers/ib-wrapper.sh",
      "args": []
    }
  }
}
```

Wrapper script (`/home/administrator/projects/mcp/proxy/wrappers/ib-wrapper.sh`):
- Forwards STDIO MCP protocol to HTTP endpoint (mcp-ib:8000/mcp)
- Enables SSE/streamable HTTP transport for Kilo Code and Claude Code CLI

### Kilo Code Configuration
Add to `.kilocode/mcp.json`:
```json
{
  "mcpServers": {
    "ib": {
      "type": "streamable-http",
      "url": "http://linuxserver.lan:9090/ib/mcp"
    }
  }
}
```

## 🛠️ Operations

### Container Management
```bash
# Start services
cd /home/administrator/projects/mcp/ib
set -a && source /home/administrator/projects/secrets/mcp-ib.env && set +a
docker compose up -d

# Check status
docker ps --filter name=mcp-ib
docker logs mcp-ib --tail 50
docker logs mcp-ib-gateway --tail 50

# Restart services
docker compose restart

# Stop services
docker compose down
```

### Health Checks
```bash
# MCP server health
curl http://localhost:48012/health

# Check if Gateway is logged in
docker logs mcp-ib-gateway | grep "Login has completed"

# Check if configuration tasks completed
docker logs mcp-ib-gateway | grep "Configuration tasks completed"

# Verify socat is running
docker exec mcp-ib-gateway ps aux | grep socat

# Test IB API connection
docker exec mcp-ib python3 -c "
from ib_insync import IB
import asyncio

async def test():
    ib = IB()
    await ib.connectAsync('ibgateway', 4004, clientId=99)
    print(f'Connected! Accounts: {ib.wrapper.accounts}')
    ib.disconnect()

asyncio.run(test())
"
```

## 🔧 Troubleshooting

### Common Issues

**Connection timeout**:
- **Symptom**: `TimeoutError` or "API connection failed"
- **Cause**: Connecting to wrong port (4002 instead of 4004)
- **Solution**: Ensure IB_PORT=4004 in environment variables
- **Verification**: `docker exec mcp-ib env | grep IB_PORT` should show 4004

**TrustedIPs not working**:
- **Symptom**: Connection refused despite updating TrustedIPs in jts.ini
- **Cause**: IB Gateway ignores TrustedIPs setting, only listens on 127.0.0.1
- **Solution**: Use socat proxy ports (4004 for paper, 4003 for live)
- **Note**: This is expected behavior, not a bug!

**IB Gateway restart loop**:
- **Symptom**: mcp-ib-gateway container continuously restarting
- **Cause**: Invalid credentials or 2FA timeout
- **Solution**: Check credentials in mcp-ib.env, verify VNC to see dialogs
- **Logs**: `docker logs mcp-ib-gateway | grep -i error`

**MCP subprocess hung**:
- **Symptom**: HTTP endpoint returns no response or timeout
- **Cause**: ib-mcp subprocess waiting for IB connection that never completes
- **Solution**: Restart mcp-ib container to recreate subprocess
- **Fix**: Ensure IB_PORT=4004 before starting

**VNC connection issues**:
- **Port**: localhost:15900
- **Password**: VNC_SERVER_PASSWORD from mcp-ib.env
- **Use**: To see IB Gateway UI and troubleshoot login dialogs

### Diagnostic Commands
```bash
# Check environment variables
docker exec mcp-ib env | grep -E "IB_HOST|IB_PORT|IB_CLIENT"
docker exec mcp-ib-gateway env | grep -E "TWS_USERID|TRADING_MODE"

# Verify network connectivity
docker exec mcp-ib getent hosts ibgateway  # Should resolve to 172.20.0.2
docker exec mcp-ib nc -zv ibgateway 4004   # Should connect successfully

# Check socat port mapping
docker exec mcp-ib-gateway ps aux | grep socat

# Test raw socket connection
docker exec mcp-ib python3 -c "
import socket
sock = socket.socket()
sock.settimeout(5)
result = sock.connect_ex(('ibgateway', 4004))
print('Port 4004:', 'OPEN' if result == 0 else 'CLOSED')
sock.close()
"

# View full Gateway logs
docker logs mcp-ib-gateway --since 5m

# Check MCP server logs
docker logs mcp-ib --since 5m | grep -E "INFO|ERROR"
```

## 📋 Standards & Best Practices

### Paper Trading Account
- **Purpose**: Development and testing only, no real money at risk
- **Data**: Real-time market data (delayed if no subscription)
- **Positions**: Simulated, resets to $1M cash periodically
- **API Limits**: Same as live account

### Security Considerations
- **Credentials**: Stored in `/home/administrator/projects/secrets/` (NOT in git)
- **Read-Only Mode**: IB_READONLY=true prevents order placement
- **API Access**: Limited to Docker network (mcp-ib-net)
- **VNC Access**: Password-protected, only on localhost:15900

### Port Configuration
- **ALWAYS use socat ports**: 4004 (paper), 4003 (live)
- **NEVER use direct ports**: 4002/4001 won't work from Docker network
- **External access**: Use Docker published ports (14002 → 4004)

## 🔄 Related Services

### Other MCP Services
- **Filesystem**: File operations (9 tools)
- **PostgreSQL**: Database queries (1 tool)
- **Puppeteer**: Browser automation (7 tools)
- **Memory**: Knowledge graph (9 tools)
- **MinIO**: S3 storage (9 tools)
- **N8N**: Workflow automation (6 tools)
- **TimescaleDB**: Time-series data (6 tools)

### Infrastructure
- **TBXark Proxy**: Unified MCP gateway on port 9090
- **MCP Middleware**: OpenAI-compatible tool execution (port 4001)
- **Docker Networks**: mcp-net (external), mcp-ib-net (internal)

## 📚 Documentation References
- **Main Documentation**: `/home/administrator/projects/mcp/CLAUDE.md`
- **Tools List**: `/home/administrator/projects/AINotes/MCPtools.md`
- **Secrets**: `/home/administrator/projects/secrets/mcp-ib.env`
- **IB Gateway Image**: https://github.com/gnzsnz/ib-gateway-docker
- **ib-mcp Package**: https://pypi.org/project/ib-mcp/

---

**Last Updated**: 2025-10-10
**Status**: ✅ Operational - Paper trading account connected and verified
**Critical Fix**: Changed IB_PORT from 4002 to 4004 (socat proxy port)
**Next Steps**: Test all 10 tools, integrate with Open WebUI via middleware
